"""客户流失 Logistic Regression 基线流水线。"""

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.churn.contracts import CATEGORICAL_FEATURE_COLUMNS, NUMERIC_FEATURE_COLUMNS


def build_logistic_pipeline(*, random_state: int = 42) -> Pipeline:
    """创建可重复使用的“预处理 + 模型”整体流水线。

    把预处理封装进 Pipeline 很重要：训练和未来预测会使用完全相同的规则，
    避免线上忘记补空值、标准化或独热编码而产生训练/预测偏差。
    """

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessing = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURE_COLUMNS),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURE_COLUMNS),
        ]
    )
    classifier = LogisticRegression(
        class_weight="balanced",
        max_iter=1_000,
        random_state=random_state,
    )
    return Pipeline(
        steps=[
            ("preprocessing", preprocessing),
            ("classifier", classifier),
        ]
    )

