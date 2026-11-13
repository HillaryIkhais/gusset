PYTHON ?= python
export PYTHONPATH := src

.PHONY: test mock live packet packages analysis receipts verify clean

## Run the pipeline tests
test:
	$(PYTHON) -m unittest discover -s tests -v

## Pipeline check only. Outputs are not evidence.
mock:
	$(PYTHON) src/experiment/run_cli.py --mock --conditions all --output reports/mock_run.json
	$(PYTHON) src/analysis/analyze.py reports/mock_run.json reports/mock_analysis.md --bootstrap 500

## Live pilot (requires NVIDIA_API_KEY; see scripts/run_live.py)
live:
	$(PYTHON) scripts/run_live.py --conditions challenge_no_new_evidence --n-runs 1 \
		--delay 10 --max-tokens 4096 --output reports/live_challenge.json

## Decision contracts, run separately from the protocol
contracts:
	$(PYTHON) scripts/run_contracts.py --input reports/live_challenge.json \
		--output reports/live_contracts.json

## Blinded annotation packets. Keep the .key.json files private.
packet:
	$(PYTHON) src/annotation/annotate.py --mode export --task initial \
		--input reports/live_challenge.json --output reports/packet_initial.csv
	$(PYTHON) src/annotation/annotate.py --mode export --task defended \
		--input reports/live_challenge.json --output reports/packet_defended.csv

## After annotators return their CSVs
import-%:
	$(PYTHON) src/annotation/annotate.py --mode import --task $* \
		--input reports/packet_$*.csv --annotator A \
		--output reports/annotations_$*_A.json

analysis:
	$(PYTHON) src/analysis/analyze.py reports/annotated.json reports/analysis.md --bootstrap 5000

receipts:
	$(PYTHON) src/receipts/generate_receipts.py --input reports/annotated.json \
		--output-dir reports/receipts

verify:
	$(PYTHON) scripts/verify_all_receipts.py reports/receipts

clean:
	rm -rf reports/mock_run.json reports/mock_analysis.md reports/mock_analysis.json reports/mock_report.pdf
