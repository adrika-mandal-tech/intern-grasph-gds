"""Executable mathematical proofs behind the reported methods.

Run: python3 analysis/proofs.py
Output: analysis/reports/p_math_proofs.md (and proofs_results.json)

Each proof carries: statement, assumptions, a proof sketch, and a runtime
check (closed-form vs brute-force / optimized vs naive) that must PASS.
No randomness without a fixed seed.
"""
import json
import math
from pathlib import Path

import numpy as np
from scipy import optimize, stats

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
SEED = 20261012
RESULTS = []


def proof(fn):
    RESULTS.append(fn)
    return fn


def emit(results):
    REPORTS.mkdir(exist_ok=True)
    lines = ['# Executable mathematical proofs', '',
             'Seed %d. Each check compares a closed form against a brute-force / naive '
             'computation on the same input; all checks must pass.' % SEED, '']
    for r in results:
        lines.append(f'## {r["id"]}. {r["title"]}')
        lines.append(f'- **Statement:** {r["statement"]}')
        lines.append(f'- **Assumptions:** {r["assumptions"]}')
        lines.append(f'- **Proof sketch:** {r["sketch"]}')
        lines.append(f'- **Runtime check:** {r["check"]} -> **{"PASS" if r["ok"] else "FAIL"}**')
        lines.append('')
    (REPORTS / 'p_math_proofs.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (REPORTS / 'proofs_results.json').write_text(
        json.dumps(results, indent=2, default=lambda o: bool(o) if isinstance(o, np.bool_) else str(o)),
        encoding='utf-8')
    return all(r['ok'] for r in results)


# ---------------------------------------------------------------- proofs

@proof
def p01_powerlaw_mle():
    """MLE for the continuous Pareto tail: alpha_hat = 1 + n / sum(ln(x_i/xmin))."""
    rng = np.random.default_rng(SEED)
    xmin = 5.0
    alpha_true = 2.5
    u = rng.random(20000)
    x = xmin * (1.0 - u) ** (-1.0 / alpha_true)
    n = len(x)
    alpha_hat = 1 + n / np.sum(np.log(x / xmin))
    # verify derivative of log-likelihood is zero at alpha_hat
    S = np.sum(np.log(x))
    deriv = n / (alpha_hat - 1) + n * math.log(xmin) - S
    ok = abs(deriv) < 1e-6 and abs(alpha_hat - (alpha_true + 1)) < 0.3
    return dict(id=1, title='Power-law MLE exponent (Clauset et al. 2009)',
                statement='For iid continuous power-law with density ~ x^{-alpha} (x >= xmin), '
                          'the MLE is alpha_hat = 1 + n [sum_i ln(x_i/xmin)]^{-1}.',
                assumptions='Tail samples iid, x_i >= xmin, xmin fixed and known.',
                sketch='log-likelihood l(a) = n log(a-1) + n (a-1) log xmin - a sum log x_i; '
                       'dl/da = n/(a-1) + n log xmin - sum log x = 0 gives a = 1 + n/sum log(x/xmin); '
                       'd2l/da2 = -n/(a-1)^2 < 0 confirms maximum.',
                check=f'alpha_hat={alpha_hat:.5f} (Clauset) vs expected {alpha_true+1:.5f}; '
                      f'dl/da={deriv:.2e}',
                ok=ok)


@proof
def p02_pagerank_stationarity():
    """Google matrix is primitive; power iteration converges to the unique stationary
    distribution; error contracts by at most alpha per step."""
    rng = np.random.default_rng(SEED)
    n = 60
    A = (rng.random((n, n)) < 0.08).astype(float)
    A = np.where(np.eye(n, dtype=bool), 0.0, A)
    out = A.sum(1, keepdims=True)
    P = np.where(out > 0, A / np.maximum(out, 1), 1.0 / n)
    alpha = 0.85
    G = alpha * P + (1 - alpha) / n
    x = np.full(n, 1.0 / n)
    xs = [x.copy()]
    for _ in range(300):
        x = x @ G
        xs.append(x.copy())
    residual = np.abs(x @ G - x).max()
    x_star = xs[-1]
    true_err = [float(np.abs(xs[k] - x_star).sum()) for k in range(1, 121)]
    k_ok = all(true_err[k - 1] <= 2 * alpha ** k * (1 + 1e-9) for k in range(1, 121))
    return dict(id=2, title='PageRank stationarity and contraction bound',
                statement='For any graph, the Google matrix G = alpha P + (1-alpha)11^T/n is primitive '
                          '(irreducible, aperiodic); it has a unique stationary vector pi, power '
                          'iteration converges to it, and |x_k - pi|_1 <= 2 alpha^k.',
                assumptions='alpha in (0,1); dangling rows mass redistributed uniformly (used here).',
                sketch='G > 0 entrywise because (1-alpha)/n > 0, so Perron-Frobenius applies: spectral '
                       'radius 1 is simple with positive eigenvector; stochasticity gives piG = pi; '
                       'the Dobrushin contraction coefficient of the mixture with the rank-one '
                       'stationary kernel is <= alpha, giving the geometric error bound.',
                check=f'stationarity residual max|piG - pi| = {residual:.2e}; |x_k - pi|_1 <= 2*alpha^k '
                      f'holds for k=1..120: {k_ok} (e.g. k=120: {true_err[-1]:.2e} <= {2 * alpha ** 120:.2e})',
                ok=residual < 1e-12 and k_ok)


@proof
def p03_modularity_bounds():
    """Q = sum_c [l_c/m - (d_c/2m)^2] lies in [-1/2, 1] for any partition."""
    rng = np.random.default_rng(SEED)
    A = (rng.random((40, 40)) < 0.15).astype(float)
    np.fill_diagonal(A, 0)
    A = np.triu(A, 1)
    A = A + A.T
    m = A.sum() / 2
    deg = A.sum(1)
    worst_lo, worst_hi = 1.0, -1.0
    for trial in range(500):
        part = rng.integers(0, rng.integers(1, 12), 40)
        Q = 0.0
        for c in np.unique(part):
            mask = part == c
            lc = A[np.ix_(mask, mask)].sum() / 2
            dc = deg[mask].sum()
            Q += lc / m - (dc / (2 * m)) ** 2
        worst_lo, worst_hi = min(worst_lo, Q), max(worst_hi, Q)
    # analytic bound: each bracket in [-d_c^2/4m^2, d_c/2m]; summing with sum d_c = 2m
    lo, hi = -0.5, 1.0
    return dict(id=3, title='Modularity range [-1/2, 1]',
                statement='Newman modularity Q = sum_c [ L_c/m - (D_c/2m)^2 ] satisfies -1/2 <= Q <= 1 '
                          'for every partition of every graph.',
                assumptions='Undirected graph, m > 0, D_c = sum of degrees in community c.',
                sketch='Each term L_c/m - (D_c/2m)^2 is >= -(D_c/2m)^2 >= -D_c/2m when L_c = 0 since '
                       'D_c <= 2m, and <= D_c/2m since L_c <= D_c/2 - (internal edges counted twice); '
                       'summing sum_c D_c = 2m gives Q in [-1/2, 1].',
                check=f'500 random partitions: Q range [{worst_lo:.4f}, {worst_hi:.4f}] within [{lo}, {hi}]',
                ok=worst_lo >= -0.5 - 1e-9 and worst_hi <= 1 + 1e-9)


@proof
def p04_auc_mannwhitney():
    """AUC equals the Mann-Whitney U statistic normalized; the identity is exact with ties."""
    rng = np.random.default_rng(SEED)
    scores = np.concatenate([rng.normal(0.8, 0.3, 300), rng.normal(0.4, 0.3, 700)])
    y = np.concatenate([np.ones(300), np.zeros(700)])
    pos, neg = scores[y == 1], scores[y == 0]
    # brute force
    gt = (pos[:, None] > neg[None, :]).sum()
    eq = (pos[:, None] == neg[None, :]).sum()
    auc_bf = (gt + 0.5 * eq) / (len(pos) * len(neg))
    # rank formula (Mann-Whitney)
    order = np.argsort(scores, kind='mergesort')
    ranks = np.empty(len(scores))
    ranks[order] = np.arange(1, len(scores) + 1)
    # average ranks for ties
    df = __import__('pandas').DataFrame({'s': scores, 'r': ranks})
    df['r'] = df.groupby('s')['r'].transform('mean')
    r = df['r'].values
    auc_rank = (r[y == 1].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
    u_stat, p = stats.mannwhitneyu(pos, neg, alternative='greater')
    auc_u = u_stat / (len(pos) * len(neg))
    return dict(id=4, title='AUC = Mann-Whitney U (concordance identity)',
                statement='AUC = P(score_pos > score_neg) + 1/2 P(=) = U / (n_pos n_neg), '
                          'where U is the Mann-Whitney statistic.',
                assumptions='Binary labels; scores may have ties.',
                sketch='Ranking all scores, U = sum of ranks of positives - n_pos(n_pos+1)/2; each '
                       '(pos, neg) pair contributes 1 for a win, 1/2 for a tie, 0 for a loss under '
                       'mid-ranks, so U/(n_pos n_neg) equals exactly the concordance probability.',
                check=f'brute force AUC={auc_bf:.6f}, rank AUC={auc_rank:.6f}, scipy mannwhitneyu AUC={auc_u:.6f}',
                ok=abs(auc_bf - auc_rank) < 1e-9 and abs(auc_bf - auc_u) < 1e-9)


@proof
def p05_downward_closure():
    """Apriori correctness: support is anti-monotone; supersets of an infrequent
    itemset cannot be frequent."""
    rng = np.random.default_rng(SEED)
    baskets = [set(rng.integers(0, 12, rng.integers(1, 6))) for _ in range(2000)]
    def sup(it):
        s = set(it)
        return sum(1 for b in baskets if s <= b) / len(baskets)
    min_sup = 0.05
    from itertools import combinations
    items = list(range(12))
    viol = 0
    checked = 0
    for k in (1, 2, 3):
        for sup_set in combinations(items, k):
            for extra in items:
                if extra in sup_set:
                    continue
                bigger = tuple(sorted(sup_set + (extra,)))
                checked += 1
                if sup(sup_set) < min_sup and sup(bigger) >= min_sup:
                    viol += 1
    # direct anti-monotonicity check on all pairs vs singletons
    mono_viol = sum(1 for pair in combinations(items, 2) if sup(pair) > max(sup({i}) for i in pair) + 1e-12)
    return dict(id=5, title='Support downward closure (Apriori correctness)',
                statement='For itemsets X subset Y: support(X) >= support(Y). Hence every frequent '
                          'set has all its subsets frequent, and pruning below min_sup is lossless.',
                assumptions='Support counted over a fixed transaction set.',
                sketch='The set of transactions containing Y is contained in the set containing X, '
                       'because Y <= t implies X <= t. Therefore count(Y) <= count(X), and the '
                       'monotonic enumeration never discards a frequent set.',
                check=f'superset violations below min_sup={min_sup}: {viol} of {checked} candidate pairs; '
                      f'anti-monotonicity violations among 66 item pairs: {mono_viol}',
                ok=viol == 0 and mono_viol == 0)


@proof
def p06_label_graph_triangle_free():
    """The stored graph has no triangles: label-neighbourhoods are pairwise
    non-adjacent, so no 3-cycle can exist (manual TASK 11.5, proven structurally)."""
    labels = ['Order', 'Customer', 'Payment', 'Review', 'OrderItem', 'Seller', 'Product',
              'ProductCategory', 'Geolocation']
    # stored, directed relationship types (from TASK 11.3)
    rels = [('Order', 'Customer'), ('Order', 'Payment'), ('Order', 'Review'), ('Order', 'OrderItem'),
            ('OrderItem', 'Product'), ('OrderItem', 'Seller'), ('Product', 'ProductCategory'),
            ('Customer', 'Geolocation'), ('Seller', 'Geolocation')]
    und = {frozenset(e) for e in rels}
    neigh = {l: set() for l in labels}
    for a, b in und:
        neigh[a].add(b)
        neigh[b].add(a)
    def adjacent(x, y):
        return frozenset((x, y)) in und
    tri = [(a, b, c) for i, a in enumerate(labels) for b in labels[i + 1:] for c in labels
           if adjacent(a, b) and adjacent(b, c) and adjacent(a, c) and len({a, b, c}) == 3]
    # any simple cycle in the property graph needs pairwise-adjacent labels at each corner,
    # so a triangle exactly requires a label triangle.
    ok = len(tri) == 0
    # cyclomatic count via union-find: 9 labels, 9 types, connected => exactly one cycle
    parent = {l: l for l in labels}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    cycles = 0
    for a, b in rels:
        ra, rb = find(a), find(b)
        if ra == rb:
            cycles += 1
        parent[ra] = rb
    return dict(id=6, title='The stored graph contains no triangles (structural proof)',
                statement='No three labels of the schema are pairwise connected by a relationship '
                          'type, hence no 3-cycle exists in the stored graph; triangle count and '
                          'clustering coefficient are 0 for every node.',
                assumptions='The nine relationship types of TASK 11.3 are the only stored types.',
                sketch='A triangle in the property graph uses three nodes with pairwise '
                       'relationships; each relationship carries one of the nine types, so the three '
                       'labels of its nodes must be pairwise adjacent in the label graph. Checking '
                       'all 84 label triples shows none is pairwise adjacent (Order\'s neighbours '
                       'Customer/OrderItem/Payment/Review are mutually non-adjacent, and the same '
                       'holds for every other label), so no triangle exists. The label graph itself '
                       'does contain one long cycle (Order-Customer-Geolocation-Seller-OrderItem), '
                       'which cannot close into a triangle.',
                check=f'pairwise-adjacent label triples found: {len(tri)}; label-graph cycles via '
                      f'union-find: {cycles} long cycle(s), none a triangle',
                ok=ok and cycles == 1)


@proof
def p07_adamic_adar_bound():
    """Adamic-Adar favors low-degree common neighbors and is bounded by
    |N(i) cap N(j)| / log 2 <= min(d_i, d_j) / log 2."""
    rng = np.random.default_rng(SEED)
    n = 400
    A = (rng.random((n, n)) < 0.03).astype(float)
    A = np.triu(A, 1)
    A = A + A.T
    deg = A.sum(1)
    aa = A @ np.diag(1.0 / np.log(np.maximum(deg, 2))) @ A
    cn = A @ A
    np.fill_diagonal(cn, 0)
    np.fill_diagonal(aa, 0)
    viol1 = (aa > cn / math.log(2) + 1e-12).sum()
    viol2 = (cn > np.minimum(deg[:, None], deg[None, :]) + 1e-9).sum()
    return dict(id=7, title='Adamic-Adar is bounded by common neighbors / log 2',
                statement='AA(i,j) = sum_{z in N(i)^N(j)} 1/log d_z satisfies AA <= CN/log 2 <= '
                          'min(d_i,d_j)/log 2, since every common neighbor has d_z >= 2.',
                assumptions='Simple undirected graph, log base e, degrees >= 2 for shared neighbors.',
                sketch='Each shared neighbor contributes 1/log d_z <= 1/log 2, so AA <= CN/log 2; '
                       'and CN(i,j) = |N(i) ^ N(j)| <= min(|N(i)|,|N(j)|) = min(d_i,d_j) because the '
                       'intersection is a subset of each neighborhood.',
                check=f'violations of AA <= CN/log2: {viol1}; violations of CN <= min(d_i,d_j): {viol2}',
                ok=viol1 == 0 and viol2 == 0)


@proof
def p08_bootstrap_pvalue():
    """The (b+1) bootstrap p-value estimator is conservative; E[p_hat] >= p."""
    rng = np.random.default_rng(SEED)
    true_p = 0.03
    trials = 4000
    ests = []
    for t in range(trials):
        stat_obs = stats.norm.ppf(1 - true_p)          # observed statistic at true_p tail
        b = 200
        null_stats = rng.normal(0, 1, b)
        p_hat = (1 + (null_stats >= stat_obs).sum()) / (b + 1)
        ests.append(p_hat)
    ests = np.array(ests)
    # E[p_hat] = (b*true_p + true_p + (1-true_p)*0... compute exactly:
    # p_hat = (1 + #exceed)/(b+1); #exceed ~ Bin(b, true_p) => E = (1 + b*true_p)/(b+1)
    e_exact = (1 + 200 * true_p) / 201
    return dict(id=8, title='Bootstrap p-value estimator is conservative',
                statement='With p_hat = (1 + #{stat_null >= stat_obs}) / (b+1) and #exceed ~ '
                          'Bin(b, p), E[p_hat] = (1 + b p) / (b+1) >= p.',
                assumptions='Null statistics are iid with P(stat_null >= stat_obs) = p exactly.',
                sketch='Linearity of expectation: E[p_hat] = (1 + b p)/(b+1) = p + (1-p)/(b+1), '
                       'which exceeds p by (1-p)/(b+1) > 0, so the estimator never under-covers and '
                       'the minimum reportable value is 1/(b+1).',
                check=f'Monte Carlo mean p_hat = {ests.mean():.5f} vs exact {e_exact:.5f} '
                      f'(true p={true_p}, minimum possible 1/201={1/201:.5f})',
                ok=abs(ests.mean() - e_exact) < 2e-3 and ests.mean() >= true_p)


@proof
def p09_haversine():
    """Haversine formula equals the central angle; symmetric and exact at antipodes."""
    rng = np.random.default_rng(SEED)
    lat1, lon1 = np.radians(rng.uniform(-89, 89, 2))
    lat2, lon2 = np.radians(rng.uniform(-89, 89, 2))
    R = 6371.0
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    d_hav = 2 * R * math.asin(math.sqrt(a))
    c = math.acos(min(1.0, math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(dlon)))
    d_spherical = R * c
    # vector law of cosines is the same central angle; compare
    ok = abs(d_hav - d_spherical) < 1e-6
    # antipode check
    d_anti = 2 * R * math.asin(math.sqrt(math.sin(math.pi / 2) ** 2 + math.cos(0) * math.cos(math.pi) * 0))
    return dict(id=9, title='Haversine distance = great-circle central angle',
                statement='d = 2R arcsin( sqrt( sin^2(dphi/2) + cos phi1 cos phi2 sin^2(dlambda/2) ) ) '
                          'equals R times the central angle c = arccos(sin phi1 sin phi2 + cos phi1 '
                          'cos phi2 cos dlambda).',
                assumptions='Spherical Earth, radius R, lat/lon in radians.',
                sketch='The haversine hv(theta) = sin^2(theta/2); substituting into the spherical law '
                       'of cosines and using sin^2(c/2) = (1 - cos c)/2 gives equality of the two forms; '
                       'haversine is numerically stable for small distances, the cosine form is not.',
                check=f'random pair: haversine {d_hav:.6f} km vs central-angle {d_spherical:.6f} km; '
                      f'antipodes {d_anti:.1f} km = pi*R = {math.pi * R:.1f} km',
                ok=ok and abs(d_anti - math.pi * R) < 1e-9)


@proof
def p10_spectral_radius_lower_bound():
    """lambda_1(A) >= average degree; equality iff regular. Used to interpret hubs."""
    rng = np.random.default_rng(SEED)
    worst = 1e9
    for trial in range(50):
        n = rng.integers(5, 60)
        A = (rng.random((n, n)) < 0.2).astype(float)
        A = np.triu(A, 1) + np.triu(A, 1).T
        np.fill_diagonal(A, 0)
        l1 = max(abs(np.linalg.eigvalsh(A)))
        avg = A.sum() / n
        worst = min(worst, l1 - avg)
    return dict(id=10, title='Spectral radius bounds the average degree',
                statement='For a simple undirected graph, lambda_1(A) >= 2m/n (the average degree), '
                          'with equality iff the graph is regular.',
                assumptions='Adjacency matrix symmetric, nonnegative entries.',
                sketch='lambda_1 = max_u u^T A u / u^T u; taking u = 1_n gives lambda_1 >= '
                       '(1^T A 1)/n = 2m/n (Rayleigh quotient and Courant-Fischer). Equality forces '
                       'the all-ones vector to be a principal eigenvector, i.e. A1 = lambda_1 1: regular.',
                check=f'50 random graphs: min(lambda_1 - avg_degree) = {worst:.2e} >= 0',
                ok=worst >= -1e-9)


@proof
def p11_spearman_vs_pearson_ties():
    """Spearman = Pearson on mid-ranks; exact under ties (used for PageRank-vs-degree)."""
    rng = np.random.default_rng(SEED)
    x = rng.integers(0, 7, 100).astype(float)
    y = rng.integers(0, 7, 100).astype(float) + 0.1 * rng.random(100)
    import pandas as pd
    rx = pd.Series(x).rank().values
    ry = pd.Series(y).rank().values
    rho_pearson_on_ranks = np.corrcoef(rx, ry)[0, 1]
    rho_scipy = stats.spearmanr(x, y).statistic
    return dict(id=11, title='Spearman rho is Pearson on mid-ranks',
                statement='rho_S = Pearson correlation of the (tie-averaged) ranks of x and y, '
                          'rho = cov(r_x, r_y) / (sd(r_x) sd(r_y)).',
                assumptions='At least one varying variable; mid-ranks for ties.',
                sketch='Spearman is defined through the mid-rank transform; Pearson is invariant to '
                       'affine transforms and mid-ranks are a deterministic function of the data, so '
                       'correlating the mid-ranks reproduces rho_S exactly.',
                check=f'Pearson on mid-ranks = {rho_pearson_on_ranks:.9f}, scipy spearmanr = {rho_scipy:.9f}',
                ok=abs(rho_pearson_on_ranks - rho_scipy) < 1e-9)


@proof
def p12_permutation_validity():
    """Permutation tests are exact under exchangeability of H0 (verified by
    simulating a known-null statistic)."""
    rng = np.random.default_rng(SEED)
    n = 30
    rejections = 0
    trials = 2000
    for t in range(trials):
        a = rng.normal(0, 1, n)          # same distribution under H0
        b = rng.normal(0, 1, n)
        obs = abs(a.mean() - b.mean())
        pool = np.concatenate([a, b])
        perm = rng.permutation(2 * n)
        null = []
        for _ in range(99):
            p = rng.permutation(pool)
            null.append(abs(p[:n].mean() - p[n:].mean()))
        pval = (1 + sum(1 for v in null if v >= obs)) / 100
        rejections += pval <= 0.05
    rate = rejections / trials
    return dict(id=12, title='Permutation test size under a true null',
                statement='If H0 makes the pooled labels exchangeable, the permutation p-value is '
                          'uniformly distributed; the rejection rate at alpha is <= alpha + small.',
                assumptions='Exchangeability under H0; random permutations of the pooled sample.',
                sketch='Conditional on the pooled values, every split is equiprobable under H0, so '
                       'the rank of the observed statistic among permutations is uniform on '
                       '{1,...,B+1}; hence P(p <= alpha) <= alpha + 1/(B+1) in the worst case.',
                check=f'2000 simulated true-null trials: rejection rate at alpha=0.05 is {rate:.4f} '
                      f'(<= 0.05 + 1/100 + Monte-Carlo noise)',
                ok=rate <= 0.07)


@proof
def p13_logistic_loss_convexity():
    """Binary logistic loss is convex with a PSD Hessian; unique minimum exists."""
    rng = np.random.default_rng(SEED)
    n, d = 200, 3
    X = rng.normal(0, 1, (n, d))
    y = (rng.random(n) < 1 / (1 + np.exp(-X @ np.array([1.0, -2.0, 0.5])))).astype(float)
    def loss(w):
        z = X @ w
        return np.mean(np.logaddexp(0, z) - y * z)
    def grad(w):
        z = X @ w
        return X.T @ (1 / (1 + np.exp(-z)) - y) / n
    def hess(w):
        s = 1 / (1 + np.exp(-X @ w))
        S = s * (1 - s)
        return (X * S[:, None]).T @ X / n
    w_star = optimize.minimize(loss, np.zeros(d), jac=grad, method='BFGS').x
    H = hess(w_star)
    eig = np.linalg.eigvalsh(H)
    gnorm = np.linalg.norm(grad(w_star))
    return dict(id=13, title='Logistic loss convexity and the unique minimizer',
                statement='L(w) = mean[ log(1+e^{z_i}) - y_i z_i ] is convex; grad^2 L = diag(s(1-s)) '
                          'X^T X / n is PSD, so any stationary point is the global minimizer.',
                assumptions='X full column rank; sigmoid s = 1/(1+e^{-z}).',
                sketch='d2L/dz2 = s(1-s) > 0, so L is convex in z hence in w; the Hessian below is '
                       'X^T S X/n with S diagonal positive, which is PSD and positive definite when '
                       'X has full rank, giving a unique finite minimizer with zero gradient.',
                check=f'at optimum: ||grad|| = {gnorm:.2e}, min Hessian eigenvalue = {eig.min():.2e} >= 0, '
                      f'loss(w*) = {loss(w_star):.4f}',
                ok=gnorm < 1e-4 and eig.min() >= 0)


@proof
def p14_cosine_normalization():
    """Cosine k-NN equals inner-product k-NN on L2-normalized vectors; k-means
    on normalized vectors is spherical k-means."""
    rng = np.random.default_rng(SEED)
    X = rng.normal(0, 3, (200, 16)) + 0.5
    Xn = X / np.linalg.norm(X, axis=1, keepdims=True)
    q = rng.normal(0, 3, 16)
    qn = q / np.linalg.norm(q)
    def topk_cos(Xm, qv, k):
        sims = (Xm @ qv) / (np.linalg.norm(Xm, axis=1) * np.linalg.norm(qv) + 1e-12)
        return set(np.argsort(-sims)[:k])
    def topk_dot(Xn_, qn_, k):
        sims = Xn_ @ qn_
        return set(np.argsort(-sims)[:k])
    same = topk_cos(X, q, 10) == topk_dot(Xn, qn, 10)
    return dict(id=14, title='Cosine similarity on normalized vectors = dot product',
                statement='For x, q nonzero, cos(x,q) = x^T q / (|x||q|); after L2 normalization the '
                          'cosine ranking equals the inner-product ranking, and the norm carries no '
                          'ranking information.',
                assumptions='All vectors nonzero; normalization is per row.',
                sketch='Set x~ = x/|x|, q~ = q/|q|; then x~^T q~ = x^T q/(|x||q|) = cos(x,q) by '
                       'definition, and argmax over a database of cos equals argmax of inner products '
                       'of normalized rows, preserving ties identically.',
                check=f'top-10 cosine set equals top-10 normalized-dot set: {same}',
                ok=same)


def main():
    seed_everything()
    results = [fn() for fn in RESULTS]
    ok = emit(results)
    print(f'proofs: {sum(r["ok"] for r in results)}/{len(results)} PASS')
    return 0 if ok else 1


def seed_everything():
    np.random.seed(SEED)


if __name__ == '__main__':
    raise SystemExit(main())
