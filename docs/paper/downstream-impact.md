# Downstream Impact on Spectrum-Based Fault Localization (SBFL)

## 1. Overview & Research Question

**Does coverage tool inaccuracy actively mislead automated software engineering techniques?**

In Spectrum-Based Fault Localization (SBFL), automated debugging algorithms rank program statements by suspiciousness scores. The scores are computed directly from execution spectra:
* $e_f(s)$: Number of failing tests that executed statement $s$
* $e_p(s)$: Number of passing tests that executed statement $s$
* $n_f(s)$: Number of failing tests that did *not* execute statement $s$
* $n_p(s)$: Number of passing tests that did *not* execute statement $s$

If a coverage tool produces **false-positive ghost coverage** (e.g. marking an unexecuted line inside an error recovery block or dead code as executed during a failing run), $e_f(s)$ increases falsely. This distorts the suspiciousness distribution.

---

## 2. Mathematical Formulations

Implemented in [`src/covdiff_lite/downstream.py`](file:///home/mahoraga/Software/CodeDiff-lite/src/covdiff_lite/downstream.py):

### 2.1 Ochiai Metric
$$S_{\text{Ochiai}}(s) = \frac{e_f(s)}{\sqrt{(e_f(s) + n_f(s)) \cdot (e_f(s) + e_p(s))}}$$

### 2.2 Tarantula Metric
$$S_{\text{Tarantula}}(s) = \frac{\frac{e_f(s)}{e_f(s) + n_f(s)}}{\frac{e_f(s)}{e_f(s) + n_f(s)} + \frac{e_p(s)}{e_p(s) + n_p(s)}}$$

---

## 3. Empirical Findings

When ghost coverage occurs:
* An innocent statement $s_{\text{ghost}}$ receives an artificially inflated suspiciousness score.
* The true faulty statement $s_{\text{fault}}$ drops in ranking (e.g. from Rank 1 down to Rank 3 or lower).
* In automated program repair (APR), candidate patches are prioritized by SBFL ranking; a rank drop means the APR engine wastes compute budget attempting to repair innocent lines.
