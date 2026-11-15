# Phase 6 — tabular ML (read-only; chronological splits, no Grasph writes)

Late-delivery target: delivered_customer_date > estimated_delivery_date.
Late: 7265/112650 = 0.064 prevalence
Review-score model n=111159, mean=4.035

## Late-delivery classifier
- train 78855, test 33795, prevalence 0.065
- AUC (HistGB): 0.7758, AUC (logistic): 0.6593
- AP (HistGB): 0.2466; AUC-0.5=+0.2758, AP-prevalence=+0.1817
