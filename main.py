import pandas as pd

a = [('BCH', 1.4118754261716584, 'negative'), ('OP', 0.008368310801492786, 'negative'), ('CFX', 0.0006234975872068664, 'negative'),('CFX', 0.0006234975872068664, 'negative')]

df = pd.DataFrame(a)

print(df.shape)
