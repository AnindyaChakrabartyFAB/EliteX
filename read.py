import pandas as pd
import db_engine

df = pd.read_sql("select * from app.clientsmet;", con=db_engine.elite_engine)
print(df.head())
