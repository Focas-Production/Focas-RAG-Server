Build the docker image and run using :
`docker compose up --build`


To test the RAG using streamlit:
```py
python3 -m venv venv
source venv/bin/activate
cd python-worker
pip install -r requirements.txt
streamlit run app.py
```
