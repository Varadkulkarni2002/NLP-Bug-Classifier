import os
import torch
import torch.nn as nn
from transformers import BertModel, BertTokenizer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLASSIFIER_PATH = os.path.join(r"models\classifier\best_model.pt")

print("=" * 60)
print(f"Loading: {CLASSIFIER_PATH}")
print("=" * 60)

ckpt = torch.load(CLASSIFIER_PATH, map_location="cpu", weights_only=False)

print(f"\nType of checkpoint: {type(ckpt)}")

if isinstance(ckpt, dict):
    print(f"\nTop-level keys ({len(ckpt.keys())}):")
    for k, v in ckpt.items():
        if isinstance(v, torch.Tensor):
            print(f"  [{k}] -> Tensor shape={v.shape}")
        elif isinstance(v, dict):
            print(f"  [{k}] -> dict with {len(v)} keys")
        else:
            print(f"  [{k}] -> {type(v).__name__} = {str(v)[:80]}")

    state = None
    if "model_state_dict" in ckpt:
        state = ckpt["model_state_dict"]
        print("\n>> Using key: model_state_dict")
    elif "state_dict" in ckpt:
        state = ckpt["state_dict"]
        print("\n>> Using key: state_dict")
    elif "model" in ckpt and isinstance(ckpt["model"], dict):
        state = ckpt["model"]
        print("\n>> Using key: model")
    else:
        tensor_keys = [k for k, v in ckpt.items() if isinstance(v, torch.Tensor)]
        if tensor_keys:
            state = {k: ckpt[k] for k in tensor_keys}
            print(f"\n>> Using raw tensor keys: {tensor_keys[:5]}")
        else:
            for k, v in ckpt.items():
                if isinstance(v, dict) and any(isinstance(vv, torch.Tensor) for vv in v.values()):
                    state = v
                    print(f"\n>> Found nested state dict under key: '{k}'")
                    break

    if state is None:
        print("\nERROR: Could not find any state dict in checkpoint!")
    else:
        print(f"\nState dict has {len(state)} keys.")
        print("\nAll keys in state dict:")
        for k, v in state.items():
            print(f"  {k:60s} shape={tuple(v.shape)}")

        print("\n--- HEAD KEY CHECK ---")
        head_keys = [k for k in state.keys() if any(h in k for h in ["head", "classifier", "fc", "linear", "output"])]
        if head_keys:
            print("Found potential head keys:")
            for k in head_keys:
                print(f"  {k} -> shape={tuple(state[k].shape)}, mean={state[k].float().mean().item():.4f}, std={state[k].float().std().item():.4f}")
        else:
            print("NO head/classifier/fc keys found — heads may be missing from checkpoint!")
            print("This means classification heads will be random (untrained) weights.")

        print("\n--- BERT KEY SAMPLE ---")
        bert_keys = [k for k in state.keys() if "bert" in k or "encoder" in k or "embeddings" in k]
        print(f"Found {len(bert_keys)} BERT-related keys")
        for k in bert_keys[:5]:
            print(f"  {k} -> shape={tuple(state[k].shape)}")

else:
    print("\nCheckpoint is NOT a dict. It is:", type(ckpt))
    print("Value:", str(ckpt)[:200])

print("\n--- TEST INFERENCE ---")

class MultiTaskClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.bert = BertModel.from_pretrained("bert-base-uncased")
        h = self.bert.config.hidden_size
        self.bug_type_head = nn.Linear(h, 5)
        self.severity_head = nn.Linear(h, 3)
        self.fix_time_head = nn.Linear(h, 3)

    def forward(self, input_ids, attention_mask):
        out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0, :]
        return self.bug_type_head(cls), self.severity_head(cls), self.fix_time_head(cls)

BUG_TYPE_LABELS = ["Crash", "Freeze", "Memory", "Other", "UI/Visual"]
SEVERITY_LABELS  = ["critical", "major", "minor"]
FIX_TIME_LABELS  = ["fast", "medium", "slow"]

mdl = MultiTaskClassifier()

if isinstance(ckpt, dict) and state is not None:
    renamed = {}
    for k, v in state.items():
        renamed[k[7:] if k.startswith("module.") else k] = v
    result = mdl.load_state_dict(renamed, strict=False)
    print(f"Missing keys:    {result.missing_keys}")
    print(f"Unexpected keys: {result.unexpected_keys[:5]}")

mdl.eval()
tok = BertTokenizer.from_pretrained("bert-base-uncased")

test_bugs = [
    "The submit button on the login page is cut off and overlaps with the footer.",
    "The application crashes when uploading a profile picture.",
    "App freezes after 10 minutes of inactivity.",
    "RAM usage climbs to 4GB on the dashboard.",
    "Fatal exception in the backend database when exporting PDF.",
]

print("\nTest classifications:")
print("-" * 60)
for text in test_bugs:
    enc = tok(text, max_length=128, padding="max_length", truncation=True, return_tensors="pt")
    with torch.no_grad():
        bt, sv, ft = mdl(enc["input_ids"], enc["attention_mask"])
    bt_probs = torch.softmax(bt, dim=1)[0].tolist()
    sv_probs = torch.softmax(sv, dim=1)[0].tolist()
    ft_probs = torch.softmax(ft, dim=1)[0].tolist()
    pred_bt = BUG_TYPE_LABELS[bt.argmax(1).item()]
    pred_sv = SEVERITY_LABELS[sv.argmax(1).item()]
    pred_ft = FIX_TIME_LABELS[ft.argmax(1).item()]
    print(f"\nInput:    {text[:70]}")
    print(f"Bug Type: {pred_bt:12s} probs={[f'{p:.2f}' for p in bt_probs]}")
    print(f"Severity: {pred_sv:12s} probs={[f'{p:.2f}' for p in sv_probs]}")
    print(f"Fix Time: {pred_ft:12s} probs={[f'{p:.2f}' for p in ft_probs]}")

print("\n" + "=" * 60)
print("If all probs are ~equal (e.g. 0.20/0.20/0.20) the heads are RANDOM.")
print("If probs are confident (e.g. 0.90/0.05/0.05) the model is TRAINED.")
print("=" * 60)