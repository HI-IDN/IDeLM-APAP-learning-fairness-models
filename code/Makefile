../data/call_schedules/%q.json: ../data/call_schedules/%q.xls xls_to_json_converter.py
	python3 xls_to_json_converter.py $< -o $@ --simple

../data/call_schedules/%q: ../data/call_schedules/%q.json quarterly_json_week_splitter.py
	python3 quarterly_json_week_splitter.py $< --outdir $@.tmp && mv $@.tmp $@

XLS=$(wildcard ../data/call_schedules/*.xls)
JSON=$(subst .xls,.json,$(XLS))
WEEKLY_DIRS=$(subst .json,,$(JSON))

all:
	make $(JSON)
	make $(WEEKLY_DIRS)
