import torch
import torch.nn as nn
import streamlit as st
from collections import OrderedDict
from transformers import BertModel, BertTokenizer
from app.helpers.config import (
    DEVICE, CLASSIFIER_PATH, MAX_TOKEN_LENGTH,
    TEMPERATURE, CONF_THRESHOLD,
    BUG_TYPE_LABELS, SEVERITY_LABELS, FIX_TIME_LABELS,
)


class AttentionPooling(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.attn = nn.Linear(hidden_size, 1)

    def forward(self, hidden_states, attention_mask):
        scores  = self.attn(hidden_states).squeeze(-1)
        mask    = (1.0 - attention_mask.float()) * -10000.0
        scores  = scores + mask
        weights = torch.softmax(scores, dim=-1).unsqueeze(-1)
        return (hidden_states * weights).sum(dim=1)


def _make_head(in_dim, out_dim):
    return nn.Sequential(OrderedDict([
        ("0", nn.Linear(in_dim, 512)),
        ("1", nn.BatchNorm1d(512)),
        ("2", nn.GELU()),
        ("3", nn.Dropout(0.3)),
        ("4", nn.Linear(512, 256)),
        ("5", nn.BatchNorm1d(256)),
        ("6", nn.GELU()),
        ("7", nn.Dropout(0.3)),
        ("8", nn.Linear(256, out_dim)),
    ]))


class MultiTaskClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.bert          = BertModel.from_pretrained("bert-base-uncased")
        h                  = self.bert.config.hidden_size
        self.attn_pooling  = AttentionPooling(h)
        self.head_bugtype  = _make_head(h, 5)
        self.head_severity = _make_head(h, 3)
        self.head_fixtime  = _make_head(h, 3)

    def forward(self, input_ids, attention_mask):
        out    = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = self.attn_pooling(out.last_hidden_state, attention_mask)
        return (
            self.head_bugtype(pooled),
            self.head_severity(pooled),
            self.head_fixtime(pooled),
        )


@st.cache_resource(show_spinner=False)
def load_classifier():
    tok = BertTokenizer.from_pretrained("bert-base-uncased")
    mdl = MultiTaskClassifier()
    ckpt        = torch.load(CLASSIFIER_PATH, map_location=DEVICE, weights_only=False)
    state       = ckpt["model_state_dict"]
    load_result = mdl.load_state_dict(state, strict=False)
    truly_missing = [
        k for k in load_result.missing_keys
        if not any(buf in k for buf in [
            "num_batches_tracked",
            "running_mean",
            "running_var",
        ])
    ]
    if truly_missing:
        raise RuntimeError(f"Classifier heads did not load — missing keys: {truly_missing}")
    mdl.to(DEVICE)
    mdl.eval()
    return tok, mdl


def classify_bug(text: str, tokenizer, model) -> dict:
    model.eval()
    enc  = tokenizer(
        text,
        max_length=MAX_TOKEN_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )
    iids = enc["input_ids"].to(DEVICE)
    mask = enc["attention_mask"].to(DEVICE)

    with torch.no_grad():
        bt_logits, sv_logits, ft_logits = model(iids, mask)

    bt_probs = torch.softmax(bt_logits / TEMPERATURE, dim=1)[0]
    sv_probs = torch.softmax(sv_logits / TEMPERATURE, dim=1)[0]
    ft_probs = torch.softmax(ft_logits / TEMPERATURE, dim=1)[0]

    bt_conf, bt_idx = bt_probs.max(0)
    sv_conf, sv_idx = sv_probs.max(0)
    ft_conf, ft_idx = ft_probs.max(0)

    bug_type = BUG_TYPE_LABELS[bt_idx.item()]
    severity  = SEVERITY_LABELS[sv_idx.item()]
    fix_time  = FIX_TIME_LABELS[ft_idx.item()]

    low_confidence = (
        bt_conf.item() < CONF_THRESHOLD or
        sv_conf.item() < CONF_THRESHOLD or
        ft_conf.item() < CONF_THRESHOLD
    )

    def top2(labels, probs):
        pairs = sorted(enumerate(probs.tolist()), key=lambda x: x[1], reverse=True)
        return [(labels[i], round(p * 100, 1)) for i, p in pairs[:2]]

    return {
        "bug_type":      bug_type,
        "severity":      severity,
        "fix_time":      fix_time,
        "bt_conf":       round(bt_conf.item() * 100, 1),
        "sv_conf":       round(sv_conf.item() * 100, 1),
        "ft_conf":       round(ft_conf.item() * 100, 1),
        "bt_candidates": top2(BUG_TYPE_LABELS, bt_probs),
        "sv_candidates": top2(SEVERITY_LABELS,  sv_probs),
        "ft_candidates": top2(FIX_TIME_LABELS,  ft_probs),
        "is_uncertain":  low_confidence,
    }