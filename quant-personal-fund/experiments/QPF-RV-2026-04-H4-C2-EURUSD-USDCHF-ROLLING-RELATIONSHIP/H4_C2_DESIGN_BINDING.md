# H4-C2 — Design Binding

**Experiment:** `QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP`
**Parent design:** `QPF-RV-2026-03-H4-ROLLING-RELATIONSHIP-STABILITY`
**Candidate:** C2 (first H4 candidate)
**Clock:** `INTERNAL_ORDINAL_NOT_UTC`

---

This experiment is **bound to the parent H4 protocol without changing it**. It confirms that C2 is
the first H4 candidate and freezes the following parent design choices verbatim:

- **Orientation:** \(\log(EURUSD)\) on \(\log(USDCHF)\).
- **Fit windows:** \(W=\{1000, 2000, 5000\}\); **evaluation length:** \(E=1000\).
- **Split:** chronological **60/20/20** (train / validation / sealed).
- **Embargoes:** **30 bars** after train and after validation.
- **Historical eligibility:** ADF p < 0.05 **and** AR(1) \(b<0\), p < 0.05, finite half-life
  under \(0<-b<1\).
- **Validation-only window selection**, then a **single sealed confirmation**.
- **Internal ordinal clock only (`NOT_UTC`)**; strict intersection; exclude exactly the maximum
  common label.
- **No statistical computation occurs in this freeze stage.**
- **No profitability or trading claim is allowed.**

The parent protocol is unchanged; this stage only produces the immutable input snapshot.
