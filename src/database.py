import os
import time
import pandas as pd
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, JSON, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

Base = declarative_base()

class Symbol(Base):
    __tablename__ = 'symbols'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False)
    is_watchlist = Column(Boolean, default=False)

class OHLCV(Base):
    __tablename__ = 'ohlcv'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    timestamp = Column(DateTime)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    interval = Column(String(10))

class Setting(Base):
    __tablename__ = 'settings'
    key = Column(String(50), primary_key=True)
    value = Column(Float, nullable=False)

class SignalLog(Base):
    __tablename__ = 'signal_logs'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(20))
    signal = Column(String(10))
    confidence = Column(Float)
    price = Column(Float)
    interval = Column(String(10))

class PerformanceStat(Base):
    __tablename__ = 'performance_stats'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    total_trades = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    profit_loss = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)

class DatabaseManager:
    def __init__(self):
        # Force reload .env to catch any changes
        load_dotenv(override=True)
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = os.getenv("DB_PORT", "3306")
        self.user = os.getenv("DB_USER", "root")
        self.password = os.getenv("DB_PASS", "")
        self.dbname = os.getenv("DB_NAME", "trading_bot")
        self.connection_type = "Pending"
        
        if not self._try_mysql():
            self._fallback_to_sqlite()

    def _try_mysql(self):
        """Attempts to connect to MySQL with a short retry loop."""
        for attempt in range(3):
            try:
                # 1. Ensure Database Exists
                temp_engine = create_engine(f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}")
                with temp_engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {self.dbname}"))
                    conn.commit()
                temp_engine.dispose()

                # 2. Main Connection
                self.engine = create_engine(
                    f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}",
                    pool_pre_ping=True,
                    pool_recycle=3600
                )
                
                # 3. Verify Connection & Init Tables
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                
                Base.metadata.create_all(self.engine)
                self.Session = sessionmaker(bind=self.engine)
                self.connection_type = "MySQL"
                return True
            except Exception:
                # Silence connection errors to avoid noise on Cloud fallback
                pass
        return False

    def _fallback_to_sqlite(self):
        """Configures local SQLite fallback."""
        self.engine = create_engine("sqlite:///trading_bot.db")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.connection_type = "SQLite (Local)"
        print("WARNING: Using local SQLite fallback (trading_bot.db)")

    def check_and_upgrade_connection(self):
        """Checks if MySQL is now available and upgrades if currently on SQLite."""
        if self.connection_type != "MySQL":
            if self._try_mysql():
                print("Connection upgraded to MySQL automatically!")
                return True
        return False

    def get_session(self):
        try:
            return self.Session()
        except Exception as e:
            print(f"Error creating session: {e}")
            # Try to re-init if session factory is broken
            self._try_mysql()
            return self.Session()

    def get_engine_url(self):
        """Returns current engine URL (masked)."""
        url = str(self.engine.url)
        if ":" in url and "@" in url:
            # Mask password
            parts = url.split(":")
            if len(parts) > 2:
                subparts = parts[2].split("@")
                if len(subparts) > 1:
                    subparts[0] = "***"
                    parts[2] = "@".join(subparts)
            return ":".join(parts)
        return url

    def update_watchlist(self, symbols_list):
        session = self.get_session()
        try:
            # Mark all as not in watchlist first
            session.query(Symbol).update({Symbol.is_watchlist: False})
            for sym in symbols_list:
                existing = session.query(Symbol).filter_by(symbol=sym).first()
                if existing:
                    existing.is_watchlist = True
                else:
                    new_sym = Symbol(symbol=sym, is_watchlist=True)
                    session.add(new_sym)
            session.commit()
        finally:
            session.close()

    def get_watchlist(self):
        session = self.get_session()
        try:
            symbols = session.query(Symbol).filter_by(is_watchlist=True).all()
            return [s.symbol for s in symbols]
        finally:
            session.close()

    def save_setting(self, key, value):
        session = self.get_session()
        try:
            setting = session.query(Setting).filter_by(key=key).first()
            if setting:
                setting.value = float(value)
            else:
                session.add(Setting(key=key, value=float(value)))
            session.commit()
        finally:
            session.close()

    def get_settings(self):
        session = self.get_session()
        try:
            settings = session.query(Setting).all()
            return {s.key: s.value for s in settings}
        finally:
            session.close()

    def log_signal(self, symbol, signal, confidence, price, interval):
        session = self.get_session()
        try:
            log = SignalLog(symbol=symbol, signal=signal, confidence=confidence, price=price, interval=interval)
            session.add(log)
            session.commit()
        finally:
            session.close()

    def update_performance(self, symbol, win, pnl):
        session = self.get_session()
        try:
            stat = session.query(PerformanceStat).filter_by(symbol=symbol).first()
            if not stat:
                stat = PerformanceStat(
                    symbol=symbol, 
                    total_trades=0, 
                    wins=0, 
                    losses=0, 
                    profit_loss=0.0, 
                    win_rate=0.0
                )
                session.add(stat)
            
            # Ensure no None values (null-safety)
            if stat.total_trades is None: stat.total_trades = 0
            if stat.wins is None: stat.wins = 0
            if stat.losses is None: stat.losses = 0
            if stat.profit_loss is None: stat.profit_loss = 0.0
            
            stat.total_trades += 1
            if win:
                stat.wins += 1
            else:
                stat.losses += 1
            
            stat.profit_loss += pnl
            if stat.total_trades > 0:
                stat.win_rate = (stat.wins / stat.total_trades) * 100
            
            session.commit()
        finally:
            session.close()

    def get_performance(self):
        session = self.get_session()
        try:
            stats = session.query(PerformanceStat).all()
            return pd.DataFrame([
                {
                    'Symbol': s.symbol,
                    'Trades': s.total_trades,
                    'Wins': s.wins,
                    'Losses': s.losses,
                    'P/L ($)': round(s.profit_loss, 2),
                    'Win Rate (%)': round(s.win_rate, 1)
                } for s in stats
            ])
        finally:
            session.close()

    def clear_performance(self):
        session = self.get_session()
        try:
            session.query(PerformanceStat).delete()
            session.commit()
            return True
        except Exception:
            return False
        finally:
            session.close()

    def get_stats(self):
        """Returns row counts for all tables."""
        session = self.get_session()
        try:
            return {
                "ohlcv": session.query(OHLCV).count(),
                "signals": session.query(SignalLog).count(),
                "performance": session.query(PerformanceStat).count(),
                "symbols": session.query(Symbol).count()
            }
        except Exception:
            return {"ohlcv": 0, "signals": 0, "performance": 0, "symbols": 0}
        finally:
            session.close()

    def clear_ohlcv(self):
        session = self.get_session()
        try:
            session.query(OHLCV).delete()
            session.commit()
            return True
        except Exception:
            return False
        finally:
            session.close()

    def save_ohlcv(self, symbol, interval, df):
        session = self.get_session()
        try:
            for timestamp, row in df.iterrows():
                # Check if this candle already exists
                existing = session.query(OHLCV).filter_by(
                    symbol=symbol, 
                    interval=interval, 
                    timestamp=timestamp
                ).first()
                
                if not existing:
                    candle = OHLCV(
                        symbol=symbol,
                        interval=interval,
                        timestamp=timestamp,
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume']
                    )
                    session.add(candle)
            session.commit()
        finally:
            session.close()

    def get_ohlcv(self, symbol, interval, limit=1000):
        session = self.get_session()
        try:
            candles = session.query(OHLCV).filter_by(
                symbol=symbol, 
                interval=interval
            ).order_by(OHLCV.timestamp.desc()).limit(limit).all()
            
            if not candles:
                return pd.DataFrame()
                
            df = pd.DataFrame([
                {
                    'timestamp': c.timestamp,
                    'open': c.open,
                    'high': c.high,
                    'low': c.low,
                    'close': c.close,
                    'volume': c.volume
                } for c in candles
            ])
            df.set_index('timestamp', inplace=True)
            return df.sort_index()
        finally:
            session.close()

    def get_last_timestamp(self, symbol, interval):
        session = self.get_session()
        try:
            last_candle = session.query(OHLCV).filter_by(
                symbol=symbol, 
                interval=interval
            ).order_by(OHLCV.timestamp.desc()).first()
            return last_candle.timestamp if last_candle else None
        finally:
            session.close()
