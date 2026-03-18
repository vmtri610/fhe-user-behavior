import pandas as pd
import joblib
import os

def preprocess_customer_data(customer_dict, scaler):
    df = pd.DataFrame([customer_dict])
    
    df['TimePerPurchase'] = df['TimeSpentOnWebsite'] / (df['NumberOfPurchases'] + 1)
    
    num_cols = ['Age', 'AnnualIncome', 'NumberOfPurchases', 'TimeSpentOnWebsite', 'DiscountsAvailed']
    df[num_cols] = scaler.transform(df[num_cols])
    
    expected_cols = [
        'Age', 'Gender', 'AnnualIncome', 'NumberOfPurchases', 
        'ProductCategory', 'TimeSpentOnWebsite', 'LoyaltyProgram', 
        'DiscountsAvailed', 'TimePerPurchase'
    ]
    df = df[expected_cols]
    
    return df

def load_model_assets():
    base_path = os.path.dirname(os.path.dirname(__file__))
    model_path = os.path.join(base_path, 'models', 'model_classification.pkl')
    scaler_path = os.path.join(base_path, 'models', 'scaler.pkl')
    
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        return None, None
        
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    
    return model, scaler
