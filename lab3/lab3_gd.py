# -*- coding: utf-8 -*-
"""
ЛР3. Градиентный спуск (вариант 15 -> нечётный -> L2-регуляризация).

Что делает скрипт:
  1. Генерирует датасет make_regression (4 признака + свободный член = 5 весов) и масштабирует его.
  2. Своя функция градиентного спуска (полный GD) и стохастического (SGD), критерий остановки ||w_k - w_{k-1}|| < eps.
  3. Эксперимент со скоростью обучения (learning rate).
  4. Сравнение GD и SGD: MSE по итерациям на одном графике.
  5. L2-регуляризация (Ridge): 20 коэффициентов от 0.001 до 1000, график весов.
Графики сохраняются в папку figures/.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")                     # рисуем в файл, окна не нужны
import matplotlib.pyplot as plt
from sklearn.datasets import make_regression
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)
SEED = 15
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10})


# ============================================================================ 1. ДАННЫЕ
def make_data():
    """4 признака (3 информативных + 1 бесполезный), шум, затем стандартизация X и y."""
    X, y = make_regression(n_samples=500, n_features=4, n_informative=3, noise=20.0, bias=5.0, random_state=SEED)
    X = StandardScaler().fit_transform(X)                      # каждый признак: среднее 0, std 1
    y = StandardScaler().fit_transform(y.reshape(-1, 1)).ravel()
    X = np.hstack([np.ones((X.shape[0], 1)), X])               # столбец единиц = свободный член w0
    return X, y


def mse(X, y, w):
    """Среднеквадратичная ошибка Q(w) = 1/n * sum (x_i w - y_i)^2."""
    r = X @ w - y
    return float(r @ r / len(y))


# ============================================================================ 2. GD и SGD
def gradient_descent(X, y, lr=0.1, n_iter=1000, eps=1e-6, stochastic=False, l2=0.0, seed=SEED, w0=None):
    """
    Градиентный спуск для линейной регрессии. Алгоритм (как в задании):
      1) инициализируем веса w и точность eps;
      2) цикл по числу итераций;
      3) w_new = w - lr * grad Q(w);
      4) выходим, если ||w_new - w|| < eps.

    stochastic=True : на каждой итерации берём ОДИН случайный объект (SGD), иначе все n (обычный GD).
    l2 > 0          : L2-регуляризация, к функции потерь добавляется l2 * ||w||^2 (свободный член не штрафуем).
    Возвращает: веса и историю MSE (на всех данных) после каждой итерации.
    """
    rng = np.random.default_rng(seed)
    n, d = X.shape
    w = np.zeros(d) if w0 is None else w0.copy()               # начальные веса
    history = [mse(X, y, w)]
    for _ in range(n_iter):
        if stochastic:
            i = rng.integers(n)                                # случайный объект
            xi, yi = X[i], y[i]
            grad = 2 * xi * (xi @ w - yi)                      # градиент по одному объекту
        else:
            grad = 2 * X.T @ (X @ w - y) / n                   # градиент по всей выборке
        if l2 > 0:
            reg = 2 * l2 * w
            reg[0] = 0.0                                       # w0 не регуляризуем
            grad = grad + reg
        w_new = w - lr * grad
        history.append(mse(X, y, w_new))
        converged = np.linalg.norm(w_new - w) < eps            # критерий остановки
        w = w_new
        if not np.isfinite(history[-1]) or history[-1] > 1e12: # расходимся - останавливаемся
            break
        if converged:
            break
    return w, np.array(history)


def section(title):
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


def main():
    X, y = make_data()
    n, d = X.shape
    section("1. ДАННЫЕ")
    print(f"Объектов: {n}, признаков: {d - 1} (+ свободный член), всего весов: {d}")

    # эталон: аналитическое решение (метод наименьших квадратов), с ним сравниваем GD
    ref = LinearRegression(fit_intercept=False).fit(X, y)
    w_ref = ref.coef_
    print("Эталонные веса (МНК, sklearn):", np.round(w_ref, 4), "| MSE =", round(mse(X, y, w_ref), 5))

    # ----------------------------------------------------------------- 3. скорость обучения
    section("2. ПОЛНЫЙ ГРАДИЕНТНЫЙ СПУСК: скорость обучения")
    # Hessian Q(w) = 2/n * X^T X; GD устойчив, если lr < 2 / lambda_max(Hessian) = 1 / lambda_max(X^T X / n)
    lam = np.linalg.eigvalsh(X.T @ X / n).max()
    lr_max = 1 / lam
    print(f"Наибольшее собственное число X^T X / n = {lam:.3f} -> GD сходится при lr < {lr_max:.3f}")
    lrs = [0.001, 0.01, 0.1, 0.5, round(lr_max * 0.95, 2), round(lr_max * 1.05, 2)]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    print(f"{'lr':>6} | {'итераций':>9} | {'итоговая MSE':>13} | {'||w - w_МНК||':>13} | статус")
    for lr in lrs:
        w, h = gradient_descent(X, y, lr=lr, n_iter=5000, eps=1e-6)
        diverged = (not np.isfinite(h[-1])) or h[-1] > 1e3
        status = "РАСХОДИТСЯ" if diverged else ("сошёлся" if len(h) - 1 < 5000 else "не успел за 5000")
        err = np.linalg.norm(w - w_ref) if not diverged else float("nan")
        print(f"{lr:>6} | {len(h) - 1:>9} | {h[-1]:>13.5f} | {err:>13.6f} | {status}")
        hh = np.minimum(h, 10)                                  # обрезаем для графика
        axes[0].plot(np.arange(1, len(hh)), hh[1:], label=f"lr={lr}")
        axes[1].plot(hh[:60], label=f"lr={lr}")
    for ax, t in zip(axes, ["Первые 5000 итераций", "Первые 60 итераций (крупно)"]):
        ax.set_title(t); ax.set_xlabel("итерация"); ax.set_ylabel("MSE (обрезано на 10)"); ax.set_yscale("log")
    axes[0].set_xscale("log")
    axes[0].legend()
    fig.suptitle("Влияние скорости обучения на градиентный спуск")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "01_learning_rates.png")); plt.close(fig)

    # ----------------------------------------------------------------- 4. GD vs SGD
    section("3. GD и SGD: сходимость")
    w_gd, h_gd = gradient_descent(X, y, lr=0.1, n_iter=3000, eps=1e-8)
    w_sgd, h_sgd = gradient_descent(X, y, lr=0.01, n_iter=3000, eps=0.0, stochastic=True)   # eps=0: считаем все итерации
    base = mse(X, y, w_ref)
    print(f"GD : итераций {len(h_gd) - 1:>5}, MSE = {h_gd[-1]:.5f}, ||w - w_МНК|| = {np.linalg.norm(w_gd - w_ref):.5f}")
    print(f"SGD: итераций {len(h_sgd) - 1:>5}, MSE = {h_sgd[-1]:.5f}, ||w - w_МНК|| = {np.linalg.norm(w_sgd - w_ref):.5f}")
    print(f"Минимум (МНК): MSE = {base:.5f}")
    thr = base * 1.05                                          # "почти минимум": в пределах 5%
    it_gd = int(np.argmax(h_gd <= thr)); it_sgd = int(np.argmax(h_sgd <= thr))
    print(f"До MSE <= {thr:.4f} (минимум + 5%): GD за {it_gd} итер. (= {it_gd * n} обращений к объектам), "
          f"SGD за {it_sgd} итер. (= {it_sgd} обращений к объектам)")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(h_gd, label="GD (lr=0.1, все 500 объектов)", lw=2)
    axes[0].plot(h_sgd, label="SGD (lr=0.01, 1 объект)", lw=1, alpha=0.85)
    axes[0].axhline(base, color="k", ls="--", lw=1, label="минимум (МНК)")
    axes[0].set_yscale("log"); axes[0].set_xlim(0, 400); axes[0].set_xlabel("итерация"); axes[0].set_ylabel("MSE")
    axes[0].set_title("MSE по итерациям (первые 400)"); axes[0].legend()
    # честное сравнение: по числу прочитанных объектов (1 итерация GD = n объектов)
    axes[1].plot(np.arange(1, len(h_gd)) * n, h_gd[1:], label="GD", lw=2)
    axes[1].plot(np.arange(1, len(h_sgd)), h_sgd[1:], label="SGD", lw=1, alpha=0.85)
    axes[1].axhline(base, color="k", ls="--", lw=1)
    axes[1].set_xscale("log"); axes[1].set_yscale("log")
    axes[1].set_xlabel("число прочитанных объектов (лог. шкала)"); axes[1].set_ylabel("MSE")
    axes[1].set_title("MSE по объёму вычислений"); axes[1].legend()
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "02_gd_vs_sgd.png")); plt.close(fig)

    # ----------------------------------------------------------------- 5. L2
    section("4. L2-РЕГУЛЯРИЗАЦИЯ (Ridge): 20 коэффициентов от 0.001 до 1000")
    alphas = np.logspace(-3, 3, 20)
    W, M = [], []
    max_diff = 0.0
    for a in alphas:
        lr = 0.5 / (1 + a)                                      # чем больше alpha, тем меньше шаг (иначе расходимся)
        w, h = gradient_descent(X, y, lr=lr, n_iter=40000, eps=1e-10, l2=a)
        W.append(w); M.append(mse(X, y, w))
    W = np.array(W)
    # проверка: sklearn.Ridge минимизирует ||y-Xw||^2 + alpha_sk*||w||^2, значит alpha_sk = alpha * n
    # (свободный член не штрафуется - как и в sklearn при fit_intercept=True)
    for k, a in enumerate(alphas):
        rd = Ridge(alpha=a * n, fit_intercept=True).fit(X[:, 1:], y)
        ref_w = np.r_[rd.intercept_, rd.coef_]
        max_diff = max(max_diff, float(np.abs(W[k] - ref_w).max()))
    print(f"Максимальное расхождение с sklearn.Ridge по всем весам и alpha: {max_diff:.2e}")
    print(f"{'alpha':>10} | " + " ".join(f"{'w' + str(j):>8}" for j in range(d)) + " |   MSE")
    for a, w, m in zip(alphas, W, M):
        print(f"{a:>10.3f} | " + " ".join(f"{v:>8.4f}" for v in w) + f" | {m:.4f}")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    names = ["w0 (свободный)", "w1 (бесполезный)", "w2", "w3", "w4"]
    for j in range(d):
        axes[0].plot(alphas, W[:, j], marker="o", ms=3, label=names[j])
    axes[0].set_xscale("log"); axes[0].set_xlabel("коэффициент регуляризации alpha (лог. шкала)")
    axes[0].set_ylabel("вес"); axes[0].set_title("Веса модели при L2-регуляризации"); axes[0].legend(fontsize=8)
    axes[1].plot(alphas, M, marker="o", ms=3, color="#c0392b")
    axes[1].set_xscale("log"); axes[1].set_xlabel("alpha (лог. шкала)"); axes[1].set_ylabel("MSE на обучающей выборке")
    axes[1].set_title("Цена регуляризации: ошибка растёт")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "03_l2_weights.png")); plt.close(fig)
    print("\nГрафики сохранены в", FIG)


if __name__ == "__main__":
    main()
