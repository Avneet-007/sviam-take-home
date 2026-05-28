"""
Evaluation harness stub.

TODO: Implement this.

Run your classifier across all 18 sessions, compare against the 5 labeled
sessions, and report your chosen metrics.
"""

from loader import load_all_sessions, load_labels
from classify import classify_session

def compute_metrics(results: list[dict], labels: dict) -> dict:
    """
    Why these metrics and not just accuracy?
 
    The two error types cost different amounts in this product:
      - False Positive (flag honest candidate): destroys their result, legal
        risk, platform trust damaged. Cost = VERY HIGH.
      - False Negative (miss a cheater): they proceed to next round; downstream
        interviews may catch them. Cost = MODERATE.
 
    So we track three metrics in priority order:
 
    1. False Accusation Rate (FAR)
    2. Cheat Detection Rate (CDR) — SECONDARY
    3. High-confidence errors — WORST CASE
    Overall accuracy is also reported but is NOT the primary goal:
    it hides the cost asymmetry between the two error types.
    """
    CLASSES = ["organic", "pasted", "ai_generated"]
 
    labeled = {r["session_id"]: r for r in results if r["session_id"] in labels}
    if not labeled:
        return {"error": "No labeled sessions found in results."}
 
    # Build confusion matrix
    confusion = {t: {p: 0 for p in CLASSES} for t in CLASSES}
    high_conf_errors = []
 
    for sid, result in labeled.items():
        true_lbl = labels[sid]
        pred_lbl = result.get("label", "organic")
        conf     = result.get("confidence", "low")
        confusion[true_lbl][pred_lbl] += 1
        if pred_lbl != true_lbl and conf == "high":
            high_conf_errors.append({
                "session_id": sid,
                "true":       true_lbl,
                "predicted":  pred_lbl,
                "confidence": conf,
                "reason":     result.get("reason", ""),
            })
 
    n       = len(labeled)
    correct = sum(confusion[c][c] for c in CLASSES)
 
    # Per-class precision / recall / false-positive rate
    per_class = {}
    for c in CLASSES:
        tp = confusion[c][c]
        fp = sum(confusion[o][c] for o in CLASSES if o != c)
        fn = sum(confusion[c][o] for o in CLASSES if o != c)
        tn = n - tp - fp - fn
        per_class[c] = {
            "precision": round(tp / (tp + fp), 3) if (tp + fp) else None,
            "recall":    round(tp / (tp + fn), 3) if (tp + fn) else None,
            "fpr":       round(fp / (fp + tn), 3) if (fp + tn) else None,
        }
 
    # PRIMARY: False Accusation Rate
    organic_sids   = [sid for sid, lbl in labels.items() if lbl == "organic"]
    false_acc_sids = [
        sid for sid in organic_sids
        if labeled.get(sid, {}).get("label") != "organic"
    ]
    far = round(len(false_acc_sids) / len(organic_sids), 3) if organic_sids else 0
 
    # SECONDARY: Cheat Detection Rate (pasted + ai_generated combined)
    cheat_sids = [sid for sid, lbl in labels.items() if lbl in ("pasted", "ai_generated")]
    detected   = [
        sid for sid in cheat_sids
        if labeled.get(sid, {}).get("label") in ("pasted", "ai_generated")
    ]
    cdr = round(len(detected) / len(cheat_sids), 3) if cheat_sids else 0
 
    return {
        "n_total":               len(results),
        "n_labeled":             n,
        "accuracy":              round(correct / n, 3) if n else 0,
        "false_accusation_rate": far,
        "false_accusations":     false_acc_sids,
        "cheat_detection_rate":  cdr,
        "high_confidence_errors": high_conf_errors,
        "per_class":             per_class,
        "confusion_matrix":      confusion,
    }
 
 
def print_report(results: list[dict], labels: dict, metrics: dict):
    CLASSES = ["organic", "pasted", "ai_generated"]
    W = 78
 
    # Results table (all 18 sessions) 
    print()
    print("Session            | Predicted       | Confidence | Ground Truth")
    print("-------------------+-----------------+------------+-------------")
    for r in results:
        sid  = r["session_id"]
        pred = r.get("label", "?")
        conf = r.get("confidence", "?")
        gt   = labels.get(sid, "—")
        flag = ""
        if gt != "—":
            flag = "  ✓" if pred == gt else "  ✗ WRONG"
        print(f"{sid:18} | {pred:15} | {conf:10} | {gt}{flag}")
 
    # Metric summary 
    print()
    print("─" * W)
    print("METRICS  (evaluated on 5 labeled sessions)")
    print("─" * W)
    print()
 
    acc = metrics["accuracy"]
    far = metrics["false_accusation_rate"]
    cdr = metrics["cheat_detection_rate"]
    hce = metrics["high_confidence_errors"]
    fa  = metrics["false_accusations"]
 
    print(f"  Overall accuracy {acc:.0%}   ({metrics['n_labeled']} labeled sessions)")
    print()
    print(f"False Accusation Rate (FAR)  {far:.0%} :PRIMARY METRIC")
    print(f" Honest candidates wrongly flagged: {fa if fa else 'none'}")
    print(f"(falsely accusing someone costs far more than missing a cheater)")
    print()
    print(f"Cheat Detection Rate  (CDR)  {cdr:.0%} :SECONDARY METRIC")
    print(f"Cheating sessions correctly caught")
    print()
    print(f"High-confidence errors{len(hce)}  :WORST-CASE METRIC")
    if hce:
        for e in hce:
            print(f"  {e['session_id']}: true={e['true']}, predicted={e['predicted']}")
            print(f"  {e['reason']}")
    else:
        print("   None — every high-confidence prediction was correct")
 
    # Per-class breakdown 
    print()
    print(f"  {'Class':<16} {'Precision':<12} {'Recall':<12} {'FP Rate'}")
    print(f"  {'─'*15} {'─'*11} {'─'*11} {'─'*8}")
    for c in CLASSES:
        m    = metrics["per_class"].get(c, {})
        prec = f"{m['precision']:.0%}" if m.get("precision") is not None else "N/A"
        rec  = f"{m['recall']:.0%}"    if m.get("recall")    is not None else "N/A"
        fpr  = f"{m['fpr']:.0%}"       if m.get("fpr")       is not None else "N/A"
        print(f"  {c:<16} {prec:<12} {rec:<12} {fpr}")
 
    #  Confusion matrix 
    print()
    print("  Confusion matrix  (rows = true label, cols = predicted)")
    print(f"  {'':>18}", end="")
    for c in CLASSES:
        print(f"  pred:{c[:8]:<9}", end="")
    print()
    for tc in CLASSES:
        print(f"  true:{tc:<13}", end="")
        for pc in CLASSES:
            val  = metrics["confusion_matrix"][tc][pc]
            flag = " *" if tc != pc and val > 0 else "  "
            print(f"  {val}{flag:<12}", end="")
        print()
 
    print()
    print("─" * W)
    print()

def evaluate():
    sessions = load_all_sessions()
    labels   = load_labels()
 
    results = []
    for session in sessions:
        result = classify_session(session)
        results.append(result)
        # small delay so we don't hammer the API rate limit
        if result.get("stage") == "llm":
            time.sleep(0.3)
 
    # Compare results against labels and compute metrics
    metrics = compute_metrics(results, labels)
 
    # Save results and metrics for inspection
    out_dir = Path(__file__).parent
    with open(out_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2)
    with open(out_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
 
    # Print results table and metric summary
    print_report(results, labels, metrics)
 
 
if __name__ == "__main__":
    evaluate()
