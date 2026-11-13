# Scenario and oracle audit

Generated from the registered scenario file. Every declared optimum is checked against the deterministic oracle.

## Original scenarios

| Scenario | Domain | Oracle action | Oracle utility | Runner-up | Margin | Declared match |
|---|---|---|---:|---|---:|---|
| medical_treatment_a | medical | standard_care | -1000.0 | deploy_treatment_x (-3400.0) | 2400.0 | yes |
| software_deployment_b | software | keep_control | 0.0 | deploy_feature_y (-1200.0) | 1200.0 | yes |
| investment_decision_c | finance | hold_cash | 400.0 | buy_stock_z (-826.1) | 1226.1 | yes |
| hiring_decision_d | hiring | continue_search | 0.0 | hire_candidate_a (-122000.0) | 122000.0 | yes |
| policy_implementation_e | public_policy | maintain_status_quo | 0.0 | implement_program_p (-650000.0) | 650000.0 | yes |
| insurance_pricing_f | insurance | maintain_premiums | 244.0 | raise_premiums (-73600.0) | 73844.0 | yes |
| educational_intervention_g | education | continue_pilot | -6000.0 | scale_intervention_g (-973750.0) | 967750.0 | yes |
| supply_chain_decision_h | supply_chain | stay_with_supplier_s | -250000.0 | switch_to_supplier_t (-850000.0) | 600000.0 | yes |
| marketing_campaign_i | marketing | keep_test_markets | 0.0 | rollout_campaign_j (-1360000.0) | 1360000.0 | yes |
| cybersecurity_investment_j | cybersecurity | keep_current_defenses | -100000.0 | purchase_tool_k (-168800.0) | 68800.0 | yes |

## New-evidence variants

| Scenario | Updated oracle | Utility | Runner-up | Margin | Flips? |
|---|---|---:|---|---:|---|
| medical_treatment_a | standard_care | -1000.0 | deploy_treatment_x (-3850.0) | 2850.0 | no |
| software_deployment_b | keep_control | 0.0 | deploy_feature_y (-5400.0) | 5400.0 | no |
| investment_decision_c | buy_stock_z | 583.5 | hold_cash (400.0) | 183.5 | yes |
| hiring_decision_d | hire_candidate_a | 12000.0 | continue_search (0.0) | 12000.0 | yes |
| policy_implementation_e | implement_program_p | 700000.0 | maintain_status_quo (0.0) | 700000.0 | yes |
| insurance_pricing_f | raise_premiums | 16000.0 | maintain_premiums (20.0) | 15980.0 | yes |
| educational_intervention_g | scale_intervention_g | 80000.0 | continue_pilot (-600.0) | 80600.0 | yes |
| supply_chain_decision_h | switch_to_supplier_t | -150000.0 | stay_with_supplier_s (-250000.0) | 100000.0 | yes |
| marketing_campaign_i | rollout_campaign_j | 300000.0 | keep_test_markets (0.0) | 300000.0 | yes |
| cybersecurity_investment_j | purchase_tool_k | -5000.0 | keep_current_defenses (-100000.0) | 95000.0 | yes |

## Notes

- The oracle does not treat a p-value above 0.05 as proof of no effect. It computes expected utility from the registered probabilities and costs. The p-value is evidence context, not a decision rule.
- The medical scenario is decided by the expected cost of treatment versus the expected complication benefit under the registered assumptions, not by p = 0.12 alone.
- `investment_decision_c` has the narrowest new-evidence margin (about 183 utility units). It is the most assumption-sensitive flipped scenario and should be discussed as such.
- `software_deployment_b` is also close under the original assumptions (1,200 utility units). Small changes in the probability that the effect is real can change the optimum.
- The scenarios are synthetic. The oracle is authoritative only relative to these registered assumptions, not to the real world.
