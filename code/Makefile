../data/call_schedules/%.json: ../data/call_schedules/%.xls call_schedule_xls_to_json.py
	python3 call_schedule_xls_to_json.py $< -o $@ --simple

XLS=$(wildcard ../data/call_schedules/*.xls)
JSON=$(subst .xls,.json,$(XLS))

all:
	make $(JSON)
