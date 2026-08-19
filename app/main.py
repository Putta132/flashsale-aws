from fastapi import FastAPI
app=FastAPI()
@app.get('/')
def r(): return {'app':'FlashSale AWS','domain':'samdevops.online'}
