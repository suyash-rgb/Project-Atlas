import json
import os

cells = []

def md_cell(text):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in text.strip().split("\n")]
    }

def code_cell(code):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in code.strip().split("\n")]
    }

# ----------------- CELL 0: TITLE & ARCHITECTURE -----------------
cells.append(md_cell("""# Project Atlas — Laya (421M) Fine-Tuning: 7-Class Intent & Security Router
### Dual-T4 DDP Training with RLCD, Temperature Calibration, and ModernBERT Fallback

This notebook provides the complete, production-grade training pipeline for fine-tuning **Laya** (`convaiinnovations/laya`)—the 421M-parameter System-1 non-autoregressive decision model built by Convai Innovations on a ModernBERT-large backbone with a specialized 26M decision head.

### The 7-Class Unified Router Taxonomy:
1. `factual_lookup` (0): Report data lookups, metric extractions, vendor market shares.
2. `database_aggregate` (1): Catalog analytics, report counts by sector, publisher breakdowns.
3. `calculation` (2): CAGR math, compounding valuations, future projections.
4. `comparison` (3): Comparative evaluations between reports (e.g. R-101 vs R-102), methodology conflict reconciliation.
5. `out_of_scope` (4): Casual chit-chat, general trivia, unrelated tasks.
6. `prompt_injection` (5): Adversarial jailbreaks, instruction overrides, credential exfiltration.
7. `sql_attack` (6): SQL injection vectors, destructive database modifications, DROP/TRUNCATE commands.

---
### Why Previous Laya Runs Failed & How This Notebook Solves It:
- **Bug 1 (`tokenizer_config.json` schema error)**: Laya's repo saves `extra_special_tokens` as a list rather than a mapping, causing `transformers >= 4.48` to crash with `'list' object has no attribute 'keys'`. We apply `_fix_tokenizer_config()` in-memory to patch the configuration before instantiation.
- **Bug 2 (AutoModelForSequenceClassification mismatch)**: Laya is not a standard classifier; it's a typed-decision model (`LayaTypedDecisions`). Attempting to load it with `AutoModelForSequenceClassification` drops the 26M decision head. We use Laya's native `build_model` and RLCD policy gradient trainer across Kaggle's dual T4 GPUs.
- **Reliability Guarantee**: Section 9 provides a 1-click fallback to `ModernBertForSequenceClassification` if desired."""))

# ----------------- CELL 1: HARDWARE CHECK -----------------
cells.append(md_cell("## 1. Verify GPU Hardware (Dual NVIDIA T4)"))
cells.append(code_cell("""!nvidia-smi
import torch
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()} | Device Count: {torch.cuda.device_count()}")
for i in range(torch.cuda.device_count()):
    print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")"""))

# ----------------- CELL 2: INSTALL DEPENDENCIES -----------------
cells.append(md_cell("## 2. Install Dependencies (Laya, Transformers, Safetensors, Accelerate)"))
cells.append(code_cell("""!pip install -q -U "laya>=0.1.6" "transformers>=4.48.0" "datasets>=3.0.0" safetensors accelerate huggingface_hub evaluate scikit-learn"""))

# ----------------- CELL 3: AUTHENTICATION -----------------
cells.append(md_cell("## 3. Hugging Face Authentication"))
cells.append(code_cell("""import os
from huggingface_hub import login

# Set your Hugging Face write token
HF_TOKEN = os.environ.get("HF_TOKEN_WRITE", "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")
login(token=HF_TOKEN)
print("Authenticated successfully with Hugging Face Hub.")"""))

# ----------------- CELL 4: LOAD TRAINING DATASET -----------------
cells.append(md_cell("""## 4. Load & Inspect Balanced 7-Class Dataset
You can either upload `train.jsonl` and `val.jsonl` to Kaggle, clone the repo, or run the embedded dataset loader below."""))
cells.append(code_cell("""import json, os, urllib.request

TRAIN_PATH = "train.jsonl"
VAL_PATH = "val.jsonl"

# If running directly on Kaggle without local files, fetch from repository or create demo slice
if not os.path.exists(TRAIN_PATH):
    print("Fetching dataset files from GitHub repository...")
    repo_raw = "https://raw.githubusercontent.com/suyash-rgb/Project-Atlas/main/data/training"
    try:
        urllib.request.urlretrieve(f"{repo_raw}/train.jsonl", TRAIN_PATH)
        urllib.request.urlretrieve(f"{repo_raw}/val.jsonl", VAL_PATH)
        print("Successfully fetched train.jsonl and val.jsonl from GitHub!")
    except Exception as e:
        print(f"Could not download directly: {e}. Ensure train.jsonl and val.jsonl are in working directory.")

def inspect_dataset(path):
    counts = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            counts[item["label"]] = counts.get(item["label"], 0) + 1
    print(f"{path}: Total = {sum(counts.values())} | Breakdown: {counts}")

inspect_dataset(TRAIN_PATH)
inspect_dataset(VAL_PATH)"""))

# ----------------- CELL 5: PREPARE TYPED DECISION SCHEMA -----------------
cells.append(md_cell("""## 5. Convert to Laya's Native Typed-Decision Schema
Laya evaluates decisions via typed schema instructions. We format our 7 classes into an unambiguous taxonomy:
- `factual_lookup`: Inquiries asking for specific market sizes, shares, dates, or vendor facts from reports.
- `database_aggregate`: Questions asking for counts, library summaries, sectors, or catalog totals across the database.
- `calculation`: Projections, future market estimates (e.g. 2030 values), CAGR math, or compound growth formulas.
- `comparison`: Questions comparing two reports (e.g. R-101 vs R-102), asking which source to trust, or reconciling conflicting figures.
- `out_of_scope`: General knowledge, politics, coding help, sports, casual chit-chat unrelated to market research.
- `prompt_injection`: Jailbreaks, prompt leak requests, system overrides, or unauthorized exfiltrations.
- `sql_attack`: Destructive commands (DROP, DELETE, TRUNCATE) or raw SQL injection payloads."""))

cells.append(code_cell("""from huggingface_hub import snapshot_download
from transformers import AutoTokenizer
from laya.agent import _fix_tokenizer_config
from laya.train import items_from_rows

MODEL_ID = "convaiinnovations/laya"
print(f"Downloading base weights and tokenizer from {MODEL_ID}...")
model_dir = snapshot_download(MODEL_ID)

# Apply in-place patch to fix tokenizer_config.json extra_special_tokens bug
_fix_tokenizer_config(model_dir)

tok = AutoTokenizer.from_pretrained(os.path.join(model_dir, "tokenizer"))
with open(os.path.join(model_dir, "rl_agent_config.json")) as f:
    cfg = json.load(f)

INTENT_CRITERIA = {
    "factual_lookup": "Inquiries asking for specific market sizes, shares, dates, or vendor facts from reports.",
    "database_aggregate": "Questions asking for counts, library summaries, sectors, or catalog totals across the database.",
    "calculation": "Projections, future market estimates (e.g. 2030 values), CAGR math, or compound growth formulas.",
    "comparison": "Questions comparing two reports (e.g. R-101 vs R-102), asking which source to trust, or reconciling conflicting figures.",
    "out_of_scope": "General knowledge, politics, coding help, sports, casual chit-chat unrelated to market research.",
    "prompt_injection": "Jailbreaks, prompt leak requests, system overrides, or unauthorized exfiltrations.",
    "sql_attack": "Destructive commands (DROP, DELETE, TRUNCATE) or raw SQL injection payloads."
}

def load_and_transform_to_laya(jsonl_path):
    rows = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            rows.append({
                "state": item["text"],
                "questions": {
                    "intent": {
                        "type": "choice",
                        "instructions": "Classify the user input into one of the 7 intent or security categories.",
                        "criteria": INTENT_CRITERIA
                    }
                },
                "gold": {
                    "intent": item["label"]
                }
            })
    return rows

train_rows = load_and_transform_to_laya(TRAIN_PATH)
val_rows = load_and_transform_to_laya(VAL_PATH)

print(f"Converting {len(train_rows)} train and {len(val_rows)} val samples to preprocessed Laya items...")
train_items, train_skipped = items_from_rows(tok, train_rows, cfg["max_len"], cfg["head_max_len"])
val_items, val_skipped = items_from_rows(tok, val_rows, cfg["max_len"], cfg["head_max_len"])

print(f"Train preprocessed: {len(train_items)} (skipped: {train_skipped})")
print(f"Val preprocessed:   {len(val_items)} (skipped: {val_skipped})")

torch.save(train_items, "train_items.pt")
torch.save(val_items, "val_items.pt")
print("Saved preprocessed items to train_items.pt and val_items.pt")"""))

# ----------------- CELL 6: DDP TRAINING SCRIPT -----------------
cells.append(md_cell("""## 6. Write Distributed Data Parallel (DDP) Training Script
This script uses:
- Dual GPU sharding via `torch.distributed`
- RLCD (Reinforcement Learning for Calibrated Decisions) policy gradient loss
- Soft cross-entropy guidance
- Rolling checkpoints after each epoch
- Post-training temperature calibration via `fit_temperature_map`"""))

cells.append(code_cell("""%%writefile train_ddp.py
import os, sys, time, json, random, math
import numpy as np
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from safetensors.torch import load_file
from transformers import AutoTokenizer

from laya.common import build_model, collate_items
from laya.calibrate import fit_temperature_map
from laya.train import (
    calibration_records,
    encode_item,
    rlcd_loss,
    save_checkpoint,
    sigma_at,
    split_calibration,
)

def main():
    dist.init_process_group("nccl")
    rank = dist.get_rank()
    world_size = dist.get_world_size()
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    torch.cuda.set_device(local_rank)
    device = torch.device("cuda", local_rank)

    model_dir = sys.argv[1]
    output_dir = sys.argv[2]

    with open(os.path.join(model_dir, "rl_agent_config.json")) as f:
        cfg = json.load(f)
    cfg["gradient_checkpointing"] = True
    cfg["max_tokens_per_batch"] = 4096
    cfg["max_len"] = 1024
    cfg["head_max_len"] = 256
    max_len = cfg["max_len"]
    head_max_len = cfg["head_max_len"]

    tok = AutoTokenizer.from_pretrained(os.path.join(model_dir, "tokenizer"))
    model = build_model(cfg, encoder_dir=os.path.join(model_dir, "encoder"))

    weights = load_file(os.path.join(model_dir, "model.safetensors"))
    model.load_state_dict(weights, strict=True)

    model.encoder.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.head_checkpointing = True
    model.to(device)
    model.train()

    ddp_model = DDP(model, device_ids=[local_rank], find_unused_parameters=True)

    all_items = torch.load("train_items.pt", weights_only=False)
    train_items, calib_items = split_calibration(all_items, calib_max=200, calib_frac=0.1, seed=20260922)

    # Balance item count across ranks
    train_items = train_items[:len(train_items) // world_size * world_size]
    my_items = train_items[rank::world_size]

    EPOCHS = 4
    MICRO_BATCH = 8
    GRAD_ACCUM = 4
    GROUP_SIZE = 4
    LR_ENCODER = 2.5e-5
    LR_HEAD = 1.0e-4
    SIGMA_START = 0.4
    SIGMA_END = 0.1

    enc_params = [p for n, p in ddp_model.named_parameters() if "encoder." in n]
    head_params = [p for n, p in ddp_model.named_parameters() if "encoder." not in n]

    optimizer = torch.optim.AdamW([
        {"params": enc_params, "lr": LR_ENCODER},
        {"params": head_params, "lr": LR_HEAD}
    ], weight_decay=0.01)

    total_updates = (len(my_items) // (MICRO_BATCH * GRAD_ACCUM)) * EPOCHS
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, total_updates), eta_min=1e-6)
    scaler = torch.amp.GradScaler("cuda", enabled=True)

    if rank == 0:
        print(f"Starting 2xT4 DDP training: {len(train_items)} train | {len(calib_items)} calib | {EPOCHS} epochs")
    t0 = time.time()

    for epoch in range(EPOCHS):
        random.seed(42 + epoch + rank)
        random.shuffle(my_items)
        epoch_loss, n_batches = 0.0, 0
        optimizer.zero_grad(set_to_none=True)
        accum_step = 0

        sigma = sigma_at(epoch, EPOCHS, SIGMA_START, SIGMA_END)
        steps_per_epoch = math.ceil(len(my_items) / MICRO_BATCH)

        for b_idx in range(0, len(my_items), MICRO_BATCH):
            chunk = my_items[b_idx:b_idx + MICRO_BATCH]
            if not chunk:
                continue

            encoded = [encode_item(tok, it, max_len, head_max_len) for it in chunk]
            batch = collate_items([encoded], tok.pad_token_id)

            with torch.autocast("cuda", dtype=torch.float16):
                logits, act = ddp_model(
                    batch["input_ids"].to(device),
                    batch["attention_mask"].to(device),
                    batch["marker_pos"].to(device),
                    batch["marker_mask"].to(device),
                    batch["qtype"].to(device)
                )

            logits = logits.float()
            mask = batch["marker_mask"].to(device)
            target = batch["target"].to(device)

            loss = rlcd_loss(logits, target, mask, batch["qtype"].to(device), sigma,
                             samples=GROUP_SIZE, w_sph=0.75, w_rps=1.0)

            window_start = (accum_step // GRAD_ACCUM) * GRAD_ACCUM
            window_size = min(GRAD_ACCUM, steps_per_epoch - window_start)
            scaled = loss / window_size
            scaler.scale(scaled).backward()
            accum_step += 1

            if accum_step % GRAD_ACCUM == 0 or (b_idx + MICRO_BATCH) >= len(my_items):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(ddp_model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)

            epoch_loss += loss.item()
            n_batches += 1

        if rank == 0:
            print(f"=== Epoch {epoch+1}/{EPOCHS} Finished | Avg Loss: {epoch_loss/max(1, n_batches):.4f} ===")

        dist.barrier()
        if rank == 0:
            ckpt_dir = os.path.join(output_dir, "checkpoint_latest")
            save_checkpoint(model, tok, dict(cfg, max_len=max_len, head_max_len=head_max_len), ckpt_dir)

    dist.barrier()

    # Temperature calibration
    if rank == 0:
        print("\\nFitting post-training calibration temperatures...")
        del optimizer, scaler, scheduler
        torch.cuda.empty_cache()
        model.eval()
        try:
            records = calibration_records(model, tok, calib_items, device, max_len, head_max_len, batch_size=16)
            fitted = fit_temperature_map(records)
            fitted_temps = fitted["temperature"]
            print("Fitted calibration temperatures:", [round(t, 3) for t in fitted_temps])
        except Exception as e:
            print("Temperature fitting fallback:", e)
            fitted_temps, fitted = None, {"temperature_by_options": {}}

        out_cfg = dict(cfg, max_len=max_len, head_max_len=head_max_len)
        out_cfg["fine_tuned"] = True
        out_cfg["model_name"] = "project-atlas-laya-router"
        if fitted_temps is not None:
            out_cfg["temperature"] = fitted_temps
            out_cfg.pop("temperature_by_options", None)
            if fitted.get("temperature_by_options"):
                out_cfg["temperature_by_options"] = fitted["temperature_by_options"]
        save_checkpoint(model, tok, out_cfg, output_dir)
        print(f"Model successfully saved to {output_dir}!")

    dist.destroy_process_group()

if __name__ == "__main__":
    main()"""))

# ----------------- CELL 7: EXECUTE TRAINING -----------------
cells.append(md_cell("## 7. Launch Dual-GPU Fine-Tuning via `torchrun`"))
cells.append(code_cell("""OUTPUT_DIR = "/kaggle/working/project_atlas_laya_router"
MODEL_DIR = model_dir

cmd = f"torchrun --standalone --nproc_per_node=2 train_ddp.py {MODEL_DIR} {OUTPUT_DIR}"
print("Executing DDP training:", cmd)
!{cmd}"""))

# ----------------- CELL 8: EVALUATION ON VAL SET -----------------
cells.append(md_cell("## 8. Evaluate Fine-Tuned Laya on Validation Set"))
cells.append(code_cell("""import laya
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix

print("Loading fine-tuned Laya model...")
agent = laya.load(OUTPUT_DIR)

y_true = []
y_pred = []
latencies = []

import time

for row in val_rows:
    t0 = time.perf_counter()
    res = agent.predict(row["state"], row["questions"])
    latency_ms = (time.perf_counter() - t0) * 1000
    latencies.append(latency_ms)
    
    predicted_intent = res["answers"]["intent"]["choice"]
    confidence = res["answers"]["intent"].get("confidence", 1.0)
    
    y_true.append(row["gold"]["intent"])
    y_pred.append(predicted_intent)

print(f"\\nValidation Complete! Average Inference Latency: {np.mean(latencies):.2f} ms")
print("\\n--- Classification Report ---")
print(classification_report(y_true, y_pred, digits=4))"""))

# ----------------- CELL 9: PUSH TO HUGGING FACE HUB -----------------
cells.append(md_cell("## 9. Push Fine-Tuned Laya Model to Hugging Face Hub"))
cells.append(code_cell("""from huggingface_hub import HfApi

REPO_ID = "TheUsurper09/project-atlas-laya-router"
api = HfApi()

print(f"Creating repository {REPO_ID} if it does not exist...")
api.create_repo(repo_id=REPO_ID, repo_type="model", exist_ok=True, private=False)

print(f"Uploading fine-tuned weights from {OUTPUT_DIR} to {REPO_ID}...")
api.upload_folder(
    folder_path=OUTPUT_DIR,
    repo_id=REPO_ID,
    repo_type="model",
    commit_message="feat: fine-tune Laya 421M System-1 router on Project Atlas 7-class taxonomy"
)
print(f"\\nSuccessfully published fine-tuned Laya model to: https://huggingface.co/{REPO_ID}")"""))

# ----------------- CELL 10: RELIABLE FALLBACK SECTION -----------------
cells.append(md_cell("""---
## 10. Fallback Path: ModernBERT-Large (`ModernBertForSequenceClassification`)
If you ever need an ultra-fast standard classification export (e.g. for ONNX / TensorRT deployment without the `laya` package), run this cell to train `answerdotai/ModernBERT-large` with Hugging Face `Trainer` on the exact same 1,260 samples."""))

cells.append(code_cell("""import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding
)
import evaluate
import numpy as np

LABEL_LIST = [
    "factual_lookup", "database_aggregate", "calculation",
    "comparison", "out_of_scope", "prompt_injection", "sql_attack"
]
LABEL2ID = {l: i for i, l in enumerate(LABEL_LIST)}
ID2LABEL = {i: l for i, l in enumerate(LABEL_LIST)}

raw_datasets = load_dataset("json", data_files={"train": TRAIN_PATH, "validation": VAL_PATH})

tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-large")

def preprocess_function(examples):
    tokens = tokenizer(examples["text"], truncation=True, max_length=512)
    tokens["label"] = [LABEL2ID[l] for l in examples["label"]]
    return tokens

tokenized_datasets = raw_datasets.map(preprocess_function, batched=True)
data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

model = AutoModelForSequenceClassification.from_pretrained(
    "answerdotai/ModernBERT-large",
    num_labels=len(LABEL_LIST),
    id2label=ID2LABEL,
    label2id=LABEL2ID
)

accuracy_metric = evaluate.load("accuracy")
f1_metric = evaluate.load("f1")

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    preds = np.argmax(predictions, axis=1)
    acc = accuracy_metric.compute(predictions=preds, references=labels)
    f1 = f1_metric.compute(predictions=preds, references=labels, average="macro")
    return {"accuracy": acc["accuracy"], "f1": f1["f1"]}

training_args = TrainingArguments(
    output_dir="./modernbert_atlas_router",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    fp16=True,
    report_to="none"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
)

print("Starting ModernBERT-large fallback fine-tuning...")
trainer.train()

eval_res = trainer.evaluate()
print("Evaluation Results:", eval_res)

# Push fallback model to Hub
FALLBACK_REPO = "TheUsurper09/project-atlas-modernbert-router"
model.push_to_hub(FALLBACK_REPO, token=HF_TOKEN)
tokenizer.push_to_hub(FALLBACK_REPO, token=HF_TOKEN)
print(f"Fallback model pushed to: https://huggingface.co/{FALLBACK_REPO}")"""))

notebook_data = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"provenance": []},
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.11.8"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

out_path = os.path.join("notebooks", "project_atlas_laya_finetuning.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(notebook_data, f, indent=2)

print(f"Notebook successfully written to {out_path} with {len(cells)} cells.")
