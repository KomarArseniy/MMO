# -*- coding: utf-8 -*-
"""
ЛР4. Бинарная классификация (датасет Healthy Meal Plan: блюдо -> "здоровое" (1) или нет (0)).

Шаги (как в задании):
  1. Импорт датасета (целевой признак is_healthy бинарный).
  2. Очистка: пропуски, дубликаты, выбросы; масштабирование.
  3. Целевая переменная и набор признаков.
  4. Модели: логистическая регрессия, SVM, CART (дерево решений).
  5. Оценка качества: accuracy, precision, recall, F1, ROC-AUC, матрицы ошибок, ROC-кривые.
Запуск:  python lab4_classification.py     (CSV ищется рядом или в ../Healthy Meal Plan Dataset/...)
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV, cross_validate
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
                             confusion_matrix, ConfusionMatrixDisplay, roc_curve)

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)
SEED = 15
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10})


def find_csv():
    for p in [os.path.join(HERE, "healthy_meal_plans.csv"),
              os.path.join(HERE, "..", "Healthy Meal Plan Dataset", "Healthy Meal Plan Dataset", "healthy_meal_plans.csv"),
              os.path.join(HERE, "..", "Healthy Meal Plan Dataset", "healthy_meal_plans.csv")]:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Не нашёл healthy_meal_plans.csv: положите его рядом со скриптом.")


def section(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def metrics(y_true, y_pred, y_score):
    return dict(accuracy=accuracy_score(y_true, y_pred),
                precision=precision_score(y_true, y_pred, zero_division=0),
                recall=recall_score(y_true, y_pred),
                f1=f1_score(y_true, y_pred),
                roc_auc=roc_auc_score(y_true, y_score))


def main():
    # ------------------------------------------------------------------ 1. импорт
    section("1. ИМПОРТ ДАТАСЕТА")
    df = pd.read_csv(find_csv())
    print("Размер:", df.shape)
    print(df.head(3).to_string())
    vc = df["is_healthy"].value_counts().sort_index()
    print(f"\nЦелевой признак is_healthy: 0 -> {vc[0]} ({vc[0] / len(df):.1%}), 1 -> {vc[1]} ({vc[1] / len(df):.1%})  <- классы НЕСБАЛАНСИРОВАНЫ")

    # ------------------------------------------------------------------ 2. очистка
    section("2. ОЧИСТКА: пропуски, дубликаты, выбросы, масштаб")
    print("Пропусков всего:", int(df.isna().sum().sum()))
    print("Полных дубликатов строк:", int(df.duplicated().sum()))
    num = ["num_ingredients", "calories", "prep_time", "protein", "fat", "carbs"]
    print("\nВыбросы по правилу IQR (1.5*IQR) в числовых признаках:")
    tot = 0
    for c in num:
        q1, q3 = df[c].quantile([0.25, 0.75]); iqr = q3 - q1
        k = int(((df[c] < q1 - 1.5 * iqr) | (df[c] > q3 + 1.5 * iqr)).sum()); tot += k
        print(f"  {c:16s} границы [{q1 - 1.5 * iqr:6.3f}; {q3 + 1.5 * iqr:6.3f}]  выбросов: {k}")
    print("Диапазон числовых признаков уже [0; 1]:", bool((df[num].min() >= 0).all() and (df[num].max() <= 1).all()),
          "-> данные были нормализованы (Min-Max) автором датасета")
    print("Вывод: чистить нечего (пропусков, дубликатов, выбросов нет). Для моделей LogReg/SVM всё равно "
          "добавим StandardScaler в pipeline (fit только на обучающей части!).")

    # ------------------------------------------------------------------ 3. признаки
    section("3. ЦЕЛЕВАЯ ПЕРЕМЕННАЯ И ПРИЗНАКИ")
    X = df.drop(columns=["is_healthy", "meal_name"])      # meal_name - текстовое название блюда (20 значений), не признак
    y = df["is_healthy"]
    print("Признаки (12):", list(X.columns))
    print("Корреляция признаков с целевой (Пирсон):")
    print(X.corrwith(y).round(3).sort_values().to_string())
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].bar(["0 (не здоровое)", "1 (здоровое)"], vc.values, color=["#7f8fa6", "#2e8b57"])
    for i, v in enumerate(vc.values):
        ax[0].text(i, v + 5, f"{v} ({v / len(df):.1%})", ha="center")
    ax[0].set_title("Распределение целевого признака"); ax[0].set_ylabel("число блюд")
    c = X.corrwith(y).sort_values()
    ax[1].barh(c.index, c.values, color=np.where(c.values < 0, "#c0392b", "#2e8b57"))
    ax[1].set_title("Корреляция признаков с is_healthy"); ax[1].set_xlabel("коэффициент Пирсона")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "01_target_and_corr.png")); plt.close(fig)

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    print(f"\nTrain: {len(Xtr)} (из них класс 1: {ytr.sum()}), Test: {len(Xte)} (класс 1: {yte.sum()}) - разбиение стратифицированное")

    # ------------------------------------------------------------------ 4. модели
    section("4. МОДЕЛИ")
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    models = {
        "Baseline (всегда 0)": DummyClassifier(strategy="most_frequent"),
        "LogReg": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=SEED)),
        "LogReg balanced": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED)),
        "SVM (RBF)": make_pipeline(StandardScaler(), SVC(kernel="rbf", random_state=SEED)),
        "SVM (RBF) balanced": make_pipeline(StandardScaler(), SVC(kernel="rbf", class_weight="balanced", random_state=SEED)),
        "CART (default)": DecisionTreeClassifier(random_state=SEED),
    }
    # CART: глубину и размер листа подбираем кросс-валидацией по F1 (без подбора дерево сильно переобучается)
    grid = GridSearchCV(DecisionTreeClassifier(class_weight="balanced", random_state=SEED),
                        {"max_depth": [3, 4, 5, 6, 8, 10, None], "min_samples_leaf": [1, 3, 5, 10]}, scoring="f1", cv=cv)
    grid.fit(Xtr, ytr)
    print("CART: лучшие параметры по F1 на кросс-валидации:", grid.best_params_, f"(F1 = {grid.best_score_:.3f})")
    models["CART (tuned, balanced)"] = grid.best_estimator_
    # SVM: подбираем C (штраф за ошибки) и gamma (ширину ядра) тоже по F1 на кросс-валидации
    gsvm = GridSearchCV(make_pipeline(StandardScaler(), SVC(kernel="rbf", class_weight="balanced")),
                        {"svc__C": [0.1, 1, 10, 100, 1000], "svc__gamma": [0.01, 0.03, 0.1, 0.3, 1]}, scoring="f1", cv=cv)
    gsvm.fit(Xtr, ytr)
    print("SVM: лучшие параметры по F1 на кросс-валидации:", gsvm.best_params_, f"(F1 = {gsvm.best_score_:.3f})")
    models["SVM (tuned, balanced)"] = gsvm.best_estimator_

    rows, fitted, scores = [], {}, {}
    for name, m in models.items():
        m.fit(Xtr, ytr)
        pred = m.predict(Xte)
        score = m.predict_proba(Xte)[:, 1] if hasattr(m, "predict_proba") else m.decision_function(Xte)
        mt = metrics(yte, pred, score)
        cvs = cross_validate(m, Xtr, ytr, cv=cv, scoring=["f1", "roc_auc"])
        mt["cv_f1"] = cvs["test_f1"].mean(); mt["cv_auc"] = cvs["test_roc_auc"].mean()
        mt["train_acc"] = accuracy_score(ytr, m.predict(Xtr))
        rows.append(pd.Series(mt, name=name)); fitted[name] = m; scores[name] = (pred, score)
    res = pd.DataFrame(rows)

    # ------------------------------------------------------------------ 5. оценка
    section("5. ОЦЕНКА КАЧЕСТВА (тестовая выборка, 100 блюд)")
    pd.set_option("display.width", 200)
    print(res.round(3).to_string())
    print("\nпояснение: accuracy/precision/recall/f1/roc_auc - на test; cv_* - среднее по 5 фолдам train; train_acc - точность на train")
    res.round(4).to_csv(os.path.join(HERE, "results.csv"), encoding="utf-8-sig")

    show = ["LogReg balanced", "SVM (tuned, balanced)", "CART (tuned, balanced)"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, name in zip(axes, show):
        cm = confusion_matrix(yte, scores[name][0])
        ConfusionMatrixDisplay(cm, display_labels=["0", "1"]).plot(ax=ax, colorbar=False, cmap="Blues")
        ax.set_title(name, fontsize=10); ax.grid(False)
        tn, fp, fn, tp = cm.ravel()
        print(f"{name:24s}: TN={tn} FP={fp} FN={fn} TP={tp}")
    fig.suptitle("Матрицы ошибок на тесте (строки - истина, столбцы - прогноз)")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "02_confusion.png")); plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.8, 5))
    for name in ["LogReg balanced", "SVM (tuned, balanced)", "CART (tuned, balanced)"]:
        fpr, tpr, _ = roc_curve(yte, scores[name][1])
        ax.plot(fpr, tpr, label=f"{name} (AUC={res.loc[name, 'roc_auc']:.2f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="случайный классификатор (0.50)")
    ax.set_xlabel("FPR (доля ложных тревог)"); ax.set_ylabel("TPR (recall)"); ax.set_title("ROC-кривые на тесте"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "03_roc.png")); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    sel = ["Baseline (всегда 0)", "LogReg balanced", "SVM (tuned, balanced)", "CART (tuned, balanced)"]
    w = 0.2
    for i, mname in enumerate(["accuracy", "precision", "recall", "f1"]):
        ax.bar(np.arange(len(sel)) + i * w, res.loc[sel, mname], w, label=mname)
    ax.set_xticks(np.arange(len(sel)) + 1.5 * w); ax.set_xticklabels(["Baseline", "LogReg", "SVM", "CART"])
    ax.set_title("Метрики на тесте"); ax.legend(fontsize=8, ncol=4, loc="upper center"); ax.set_ylim(0, 1.15)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "04_metrics.png")); plt.close(fig)

    tree = fitted["CART (tuned, balanced)"]
    fig, ax = plt.subplots(figsize=(11, 5))
    plot_tree(tree, feature_names=list(X.columns), class_names=["0", "1"], filled=True, rounded=True, fontsize=7, ax=ax, max_depth=3)
    ax.set_title("CART: верхние 3 уровня дерева")
    fig.savefig(os.path.join(FIG, "05_tree.png")); plt.close(fig)
    imp = pd.Series(tree.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("\nВажность признаков в CART:\n" + imp.head(5).round(3).to_string())
    lr = fitted["LogReg balanced"][-1]
    coef = pd.Series(lr.coef_[0], index=X.columns).sort_values()
    print("\nКоэффициенты логистической регрессии (на стандартизованных признаках):\n" + coef.round(3).to_string())
    print("\nГрафики сохранены в", FIG)


if __name__ == "__main__":
    main()
