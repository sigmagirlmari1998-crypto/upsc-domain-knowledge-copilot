



from fastapi import FastAPI 

app = FastAPI() 

@app.get("/") 
def home():
    return {"message":"UPSC Domain Knowledge Copilot"}

    