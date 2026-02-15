"""Centralized configuration for the Intrusion Detection System."""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# NSL-KDD dataset files
TRAIN_FILE = RAW_DATA_DIR / "KDDTrain+.txt"
TEST_FILE = RAW_DATA_DIR / "KDDTest+.txt"

# NSL-KDD column names (41 features + label + difficulty_level)
COLUMN_NAMES = [
    "duration", "protocol_type", "service", "flag",
    "src_bytes", "dst_bytes", "land", "wrong_fragment", "urgent",
    "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations",
    "num_shells", "num_access_files", "num_outbound_cmds",
    "is_host_login", "is_guest_login",
    "count", "srv_count", "serror_rate", "srv_serror_rate",
    "rerror_rate", "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
    "srv_diff_host_rate",
    "dst_host_count", "dst_host_srv_count", "dst_host_same_srv_rate",
    "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
    "dst_host_srv_serror_rate", "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate",
    "label", "difficulty_level",
]

# Categorical and numerical feature lists
CATEGORICAL_FEATURES = ["protocol_type", "service", "flag"]
BINARY_FEATURES = [
    "land", "logged_in", "root_shell", "su_attempted",
    "is_host_login", "is_guest_login",
]
NUMERICAL_FEATURES = [
    col for col in COLUMN_NAMES
    if col not in CATEGORICAL_FEATURES + BINARY_FEATURES + ["label", "difficulty_level"]
]

# Attack type to category mapping for NSL-KDD
ATTACK_CATEGORY_MAP = {
    "normal": "Benign",
    # DoS attacks
    "back": "DoS", "land": "DoS", "neptune": "DoS", "pod": "DoS",
    "smurf": "DoS", "teardrop": "DoS", "apache2": "DoS",
    "udpstorm": "DoS", "processtable": "DoS", "worm": "DoS", "mailbomb": "DoS",
    # Probe attacks
    "satan": "Probe", "ipsweep": "Probe", "nmap": "Probe", "portsweep": "Probe",
    "mscan": "Probe", "saint": "Probe",
    # R2L attacks
    "guess_passwd": "R2L", "ftp_write": "R2L", "imap": "R2L", "phf": "R2L",
    "multihop": "R2L", "warezmaster": "R2L", "warezclient": "R2L", "spy": "R2L",
    "xlock": "R2L", "xsnoop": "R2L", "snmpguess": "R2L",
    "snmpgetattack": "R2L", "httptunnel": "R2L", "sendmail": "R2L", "named": "R2L",
    # U2R attacks
    "buffer_overflow": "U2R", "loadmodule": "U2R", "rootkit": "U2R",
    "perl": "U2R", "sqlattack": "U2R", "xterm": "U2R", "ps": "U2R",
}

# Model training config
RANDOM_SEED = 42
TEST_SPLIT_RATIO = 0.2
CV_FOLDS = 5

# Hyperparameter grids for tuning
HYPERPARAMETER_GRIDS = {
    "random_forest": {
        "n_estimators": [100, 200, 300],
        "max_depth": [10, 20, 30, None],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
        "class_weight": ["balanced"],
    },
    "xgboost": {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 6, 10],
        "learning_rate": [0.01, 0.1, 0.3],
        "subsample": [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0],
    },
    "lightgbm": {
        "n_estimators": [100, 200, 300],
        "max_depth": [-1, 10, 20],
        "learning_rate": [0.01, 0.1, 0.3],
        "num_leaves": [31, 63, 127],
        "subsample": [0.8, 1.0],
    },
    "logistic_regression": {
        "C": [0.01, 0.1, 1.0, 10.0],
        "max_iter": [1000],
        "class_weight": ["balanced"],
    },
}

# Reduced grids for faster initial training
FAST_HYPERPARAMETER_GRIDS = {
    "random_forest": {
        "n_estimators": [200],
        "max_depth": [20],
        "min_samples_split": [2],
        "min_samples_leaf": [1],
        "class_weight": ["balanced"],
    },
    "xgboost": {
        "n_estimators": [200],
        "max_depth": [6],
        "learning_rate": [0.1],
        "subsample": [0.8],
        "colsample_bytree": [0.8],
    },
    "lightgbm": {
        "n_estimators": [200],
        "max_depth": [-1],
        "learning_rate": [0.1],
        "num_leaves": [63],
        "subsample": [0.8],
    },
    "logistic_regression": {
        "C": [1.0],
        "max_iter": [1000],
        "class_weight": ["balanced"],
    },
}

# API config
API_HOST = "0.0.0.0"
API_PORT = 8000
