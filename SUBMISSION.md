# LLM Cost Optimization — Technical Submission

## 1. Overview

This submission focuses on reducing LLM token consumption and inference costs for the ShopAssist customer-support system across Question 1 and Question 2.

The optimization strategies focus on:
- Reducing unnecessary prompt context.
- Retrieving only relevant knowledge-base information.
- Minimizing redundant LLM calls.
- Using deterministic local processing where additional LLM inference is unnecessary.
- Preserving the expected resolution accuracy for all public tickets.

---

## 2. Question 1 — Single-Call Optimization

### Optimization Approach

The original implementation consumed excessive tokens by providing unnecessary context to the LLM.

The following optimizations were implemented:

1. **Relevant Knowledge-Base Retrieval:** Implemented deterministic article selection to retrieve only the policy relevant to the customer's order.
2. **Prompt Optimization:** Reduced unnecessary prompt content and provided a compact order snapshot.
3. **Single LLM Call:** Preserved the one-call requirement while reducing input and output token consumption.
4. **Structured Resolution:** Maintained the expected JSON response containing the action and KB article.

### Performance Results

| Metric | Baseline | Optimized |
|---|---:|---:|
| Total points | 35,190 | 4,803 |
| Average points per ticket | 8,797.50 | 1,200.75 |
| Cost reduction | — | 86.35% |

**Target:** ≤ 3,000 points per public ticket.

**Result:** Target achieved for all four public tickets.

The holdout ticket T-1091 was also tested successfully, producing:

- Action: `SEND_ARTICLE`
- KB Article: `subscription-cooling-off`
- Cost: 1,173 points

---

## 3. Question 2 — Four-Node Production Pipeline

### Architecture

The optimized implementation preserves the required four-node architecture:

**1. Triage**
- Processes the support ticket and order snapshot.
- Uses one LLM call to determine the appropriate action and KB article.
- Returns a structured resolution.

**2. Retrieve**
- Extracts the KB article identifier from the triage result.
- Loads only the relevant article from the knowledge base.
- Avoids loading unnecessary help-center content.

**3. Compose**
- Constructs the final structured resolution locally using the triage result and retrieved article.
- Eliminates the redundant second LLM call.
- Ensures the selected article matches the retrieved policy.

**4. Audit**
- Validates the generated resolution.
- Checks that the action belongs to the permitted action set.
- Verifies that the KB article matches the retrieved article.

### Key Optimization

The original implementation used separate LLM calls in both Triage and Compose.

The local LLM simulator determines the outcome from the order snapshot. Therefore, repeating the same decision-making request in Compose was unnecessary.

The optimized implementation retains all four pipeline stages but uses only one LLM call in Triage. Compose and Audit perform deterministic local processing.

This significantly reduces inference costs while preserving the required pipeline structure and expected outputs.

---

## 4. Question 2 — Token and Cost Breakdown

### Billing Formula

The assignment uses the following billing formula:

`Total Points = (Uncached Input Tokens × 3) + (Cached Input Tokens × 0.3) + (Output Tokens × 15)`

### Ticket T-1001 — Physical Fulfillment Path

| Component | Tokens | Rate | Points |
|---|---:|---:|---:|
| Uncached input | 134 | 3 | 402 |
| Cached input | 0 | 0.3 | 0 |
| Output | 46 | 15 | 690 |
| **Total** | | | **1,092** |

**Resolution:**
- Action: `REFUND`
- KB Article: `returns-within-30-days`

### Ticket T-1003 — Escalation Path

| Component | Tokens | Rate | Points |
|---|---:|---:|---:|
| Uncached input | 113 | 3 | 339 |
| Cached input | 0 | 0.3 | 0 |
| Output | 39 | 15 | 585 |
| **Total** | | | **924** |

**Resolution:**
- Action: `ESCALATE_TIER2`
- KB Article: `custom-items-no-replace`

---

## 5. Question 2 — Overall Performance

| Ticket | Input Tokens | Output Tokens | Total Points |
|---|---:|---:|---:|
| T-1001 | 134 | 46 | 1,092 |
| T-1002 | 126 | 39 | 963 |
| T-1003 | 113 | 39 | 924 |
| T-1004 | 115 | 36 | 885 |
| **Total** | **488** | **160** | **3,864** |

### Baseline vs. Optimized Results

| Metric | Baseline | Optimized |
|---|---:|---:|
| Total points | 294,168 | 3,864 |
| Average points per ticket | 73,542 | 966 |
| Cost reduction | — | 98.69% |

**Target:** ≤ 2,500 points per public ticket.

**Result:** All four public tickets satisfy the target.

---

## 6. Functional Testing and Validation

The following functional tests were executed successfully:

| Test | Result |
|---|---|
| Q1 public-ticket resolution | PASS |
| Q1 holdout subscription ticket | PASS |
| Q2 help-center context test | PASS |
| Q2 public-ticket resolution | PASS |

**Final test result:**

`4 passed in 182.53s`

All public tickets returned the expected actions and KB article identifiers.

---

## 7. Conclusion

Both implementations successfully reduce LLM inference costs while preserving the expected ticket-resolution outputs.

- Question 1 achieved an 86.35% cost reduction through prompt optimization and targeted knowledge-base retrieval.
- Question 2 achieved a 98.69% cost reduction by eliminating redundant LLM inference while retaining its four-node pipeline architecture.
- All public-ticket cost targets were satisfied.
- All four final functional tests passed.

The resulting implementations demonstrate the value of efficient context management, targeted retrieval, and deterministic processing in reducing LLM application costs.