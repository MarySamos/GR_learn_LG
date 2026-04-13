import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, learning_curve, StratifiedKFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import os

# 确保图片保存路径
output_dir = r"g:\PycharmProjects\BankAgent-Pro\write\images"
os.makedirs(output_dir, exist_ok=True)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def main():
    # 1. 加载真实数据集
    df = pd.read_csv(r"g:\PycharmProjects\BankAgent-Pro\data\raw\bank.csv")
    
    # 2. 数据预处理
    df['deposit'] = df['deposit'].map({'yes': 1, 'no': 0})
    
    categorical_cols = ['job', 'marital', 'education', 'default', 'housing', 'contact', 'month', 'poutcome', 'loan']
    numeric_cols = ['age', 'balance', 'duration', 'campaign', 'pdays', 'previous']
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols)
        ])
    
    X = preprocessor.fit_transform(df.drop(['deposit', 'day'], axis=1))
    y = df['deposit']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 3. 构建模型
    models = {
        '决策树': DecisionTreeClassifier(max_depth=10, min_samples_split=5, min_samples_leaf=2, random_state=42),
        '逻辑回归': LogisticRegression(max_iter=1000, C=1.0, random_state=42),
        '随机森林': RandomForestClassifier(n_estimators=100, max_depth=None, min_samples_split=2, random_state=42)
    }

    metrics_results = {}
    
    fig_cm, axes_cm = plt.subplots(1, 3, figsize=(18, 5))
    
    for idx, (name, model) in enumerate(models.items()):
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else y_pred
        
        cm = confusion_matrix(y_test, y_pred)
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        
        metrics_results[name] = [acc, prec, rec, f1, auc]
        
        # 打印输出供解析
        print(f"=== {name} ===")
        print(f"TN={cm[0,0]}, FP={cm[0,1]}, FN={cm[1,0]}, TP={cm[1,1]}")
        print(f"Accuracy={acc:.4f}, Precision={prec:.4f}, Recall={rec:.4f}, F1={f1:.4f}, AUC={auc:.4f}")
        
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes_cm[idx], cbar=False)
        axes_cm[idx].set_title(f'{name} - 混淆矩阵')
        axes_cm[idx].set_xlabel('预测值')
        axes_cm[idx].set_ylabel('真实值')
        
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'confusion_matrices.png'))
    
    # 绘制对比图
    metrics_df = pd.DataFrame(metrics_results, index=['Accuracy', 'Precision', 'Recall', 'F1_Score', 'AUC']).T
    ax = metrics_df.plot(kind='bar', figsize=(10, 6), colormap='viridis')
    plt.title('各模型性能评估指标对比')
    plt.ylabel('数值的范围')
    plt.xticks(rotation=0)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'model_comparison.png'))
    
    # 使用原生 matplotlib + for循环绘制学习曲线，避开 sklearn 的内部交叉验证报错
    fig_lc, axes_lc = plt.subplots(1, 3, figsize=(18, 5))
    
    # 选取 5 个训练集的阶段比例: 20%, 40%, 60%, 80%, 100% 
    fractions = [0.2, 0.4, 0.6, 0.8, 1.0]

    for idx, (name, model) in enumerate(models.items()):
        train_scores = []
        test_scores = []
        train_sizes = []
        
        for frac in fractions:
            # 截取对应比例的训练样本
            limit = int(len(X_train) * frac)
            X_subset = X_train[:limit]
            
            # 兼容 Pandas 的数据结构截取
            if hasattr(y_train, 'iloc'):
                y_subset = y_train.iloc[:limit]
            else:
                y_subset = y_train[:limit]
            
            # 手动塞进模型去学习（这个时候绝对不切分）
            try:
                model.fit(X_subset, y_subset)
            except ValueError:
                # 遇到极端小概率拿不到2种类别的数据，直接跳过当前这个点画图
                continue
                
            # 分别算出在它背的这撮数据和真正的测试集上的测试准度
            pred_train = model.predict(X_subset)
            pred_test = model.predict(X_test)
            
            train_scores.append(accuracy_score(y_subset, pred_train))
            test_scores.append(accuracy_score(y_test, pred_test))
            train_sizes.append(limit)
            
        # 开始调用 matplotlib 画图 (也就是你说的 matpilt)
        axes_lc[idx].plot(train_sizes, train_scores, 'o-', color='blue', label='训练集准确率')
        axes_lc[idx].plot(train_sizes, test_scores, 's-', color='green', label='验证集准确率')
        axes_lc[idx].set_title(f'{name} 学习曲线')
        axes_lc[idx].set_xlabel('训练样本数量')
        axes_lc[idx].set_ylabel('准确率')
        axes_lc[idx].legend()
        axes_lc[idx].grid()
        
        
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'learning_curves.png'))
    
    # 让图片直接弹窗显示出来！
    plt.show()
if __name__ == "__main__":
    main()
