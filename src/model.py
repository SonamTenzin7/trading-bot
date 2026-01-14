import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

class SignalModel:
    def __init__(self):
        # using sklearn GradientBoostingClassifier as drop-in replacement
        self.model = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
        self.feature_cols = [
            'rsi', 'macd', 'macd_signal', 'macd_diff', 
            'bb_high', 'bb_low', 'sma_20', 'ema_50', 'volume_change'
        ]
        self.model_path = "model.joblib"

    def prepare_data(self, df):
        # Drop rows with NaNs in features
        data = df.dropna(subset=self.feature_cols + ['target']).copy()
        
        X = data[self.feature_cols]
        # Map targets: -1->0, 0->1, 1->2
        y = data['target'].map({-1: 0, 0: 1, 1: 2})
        return X, y

    def train(self, df):
        X, y = self.prepare_data(df)
        if len(X) < 50:
            print("Not enough data to train.")
            return

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        if len(y_train.unique()) < 2:
            raise ValueError("Training data contains only one class. Training requires at least two classes (e.g., BUY and HOLD). Try increasing the training lookback or selecting a different coin/interval.")

        self.model.fit(X_train, y_train)
        
        preds = self.model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        print(f"Model Training Accuracy: {acc:.2f}")
        print(classification_report(y_test, preds))
        
        joblib.dump(self.model, self.model_path)
        return acc

    def predict(self, df):
        """
        Predicts signal for the latest available data point (or full df).
        Returns dataframe with 'prediction' and 'proba'.
        """
        data = df[self.feature_cols].copy()
        # Handle recent NaN if any (fill or drop? if latest is NaN we can't predict)
        # For safety, let's assuming forward fill or drop.
        
        # If we just want latest prediction:
        if len(data) == 0:
            return None
        
        preds = self.model.predict(data)
        probs = self.model.predict_proba(data)
        
        # Map back: 0->Sell, 1->Hold, 2->Buy
        class_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        df['signal'] = [class_map[p] for p in preds]
        df['confidence'] = [max(prob) for prob in probs]
        
        return df
