# Aircraft fault term normalizer

Enter an aircraft maintenance or fault report paragraph. Local Ollama returns one short uppercase term, for example **WHEEL NOISE**, **ENGINE VIBRATION**, or **HYDRAULIC LEAK**. The paragraph is input context; the output is a 2 to 5 word label, not a rewritten paragraph.

Click **Normalize paragraph** to generate the term. Review the generated term and click **Approve & save** to save the original paragraph, normalized term, model and approval time in `data/approved_aircraft_faults.db`. Unapproved results are not saved. Approved records appear in the table below the form. Identical paragraph and term pairs are stored only once. Back up this SQLite file to preserve your approvals. Editing the paragraph clears the previous result.

The model is prompted to label the main reported component and symptom without inventing a cause or diagnosis. Negated symptoms are excluded. Unclear or unrelated reports return **UNCLEAR FAULT**. Reports with multiple equally emphasized faults return **MULTIPLE FAULTS**. Labels are model-generated and should be reviewed; they are not validated against an approved aircraft terminology dictionary.

## Run locally

Keep Ollama running with `llama3.2:latest` installed. Select another installed model in the sidebar or set `OLLAMA_MODEL`.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

The app sends the paragraph to `http://127.0.0.1:11434/api/chat`. No paid API key is required. Input is limited to 10,000 characters, with a 120-second request timeout.

Streamlit Cloud cannot reach Ollama on your laptop. This version needs a cloud-accessible model backend before it can work as a hosted app.

The previous `mapper.py`, its tests, mapping database and `new-project/` are retained but are not used by the main interface.

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```
