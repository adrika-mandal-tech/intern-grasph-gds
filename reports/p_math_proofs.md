# Executable mathematical proofs

Seed 20261012. Each check compares a closed form against a brute-force / naive computation on the same input; all checks must pass.

## 1. Power-law MLE exponent (Clauset et al. 2009)
- **Statement:** For iid continuous power-law with density ~ x^{-alpha} (x >= xmin), the MLE is alpha_hat = 1 + n [sum_i ln(x_i/xmin)]^{-1}.
- **Assumptions:** Tail samples iid, x_i >= xmin, xmin fixed and known.
- **Proof sketch:** log-likelihood l(a) = n log(a-1) + n (a-1) log xmin - a sum log x_i; dl/da = n/(a-1) + n log xmin - sum log x = 0 gives a = 1 + n/sum log(x/xmin); d2l/da2 = -n/(a-1)^2 < 0 confirms maximum.
- **Runtime check:** alpha_hat=3.51176 (Clauset) vs expected 3.50000; dl/da=-7.28e-12 -> **PASS**

## 2. PageRank stationarity and contraction bound
- **Statement:** For any graph, the Google matrix G = alpha P + (1-alpha)11^T/n is primitive (irreducible, aperiodic); it has a unique stationary vector pi, power iteration converges to it, and |x_k - pi|_1 <= 2 alpha^k.
- **Assumptions:** alpha in (0,1); dangling rows mass redistributed uniformly (used here).
- **Proof sketch:** G > 0 entrywise because (1-alpha)/n > 0, so Perron-Frobenius applies: spectral radius 1 is simple with positive eigenvector; stochasticity gives piG = pi; the Dobrushin contraction coefficient of the mixture with the rank-one stationary kernel is <= alpha, giving the geometric error bound.
- **Runtime check:** stationarity residual max|piG - pi| = 6.94e-18; |x_k - pi|_1 <= 2*alpha^k holds for k=1..120: True (e.g. k=120: 0.00e+00 <= 6.78e-09) -> **PASS**

## 3. Modularity range [-1/2, 1]
- **Statement:** Newman modularity Q = sum_c [ L_c/m - (D_c/2m)^2 ] satisfies -1/2 <= Q <= 1 for every partition of every graph.
- **Assumptions:** Undirected graph, m > 0, D_c = sum of degrees in community c.
- **Proof sketch:** Each term L_c/m - (D_c/2m)^2 is >= -(D_c/2m)^2 >= -D_c/2m when L_c = 0 since D_c <= 2m, and <= D_c/2m since L_c <= D_c/2 - (internal edges counted twice); summing sum_c D_c = 2m gives Q in [-1/2, 1].
- **Runtime check:** 500 random partitions: Q range [-0.1064, 0.1170] within [-0.5, 1.0] -> **PASS**

## 4. AUC = Mann-Whitney U (concordance identity)
- **Statement:** AUC = P(score_pos > score_neg) + 1/2 P(=) = U / (n_pos n_neg), where U is the Mann-Whitney statistic.
- **Assumptions:** Binary labels; scores may have ties.
- **Proof sketch:** Ranking all scores, U = sum of ranks of positives - n_pos(n_pos+1)/2; each (pos, neg) pair contributes 1 for a win, 1/2 for a tie, 0 for a loss under mid-ranks, so U/(n_pos n_neg) equals exactly the concordance probability.
- **Runtime check:** brute force AUC=0.825438, rank AUC=0.825438, scipy mannwhitneyu AUC=0.825438 -> **PASS**

## 5. Support downward closure (Apriori correctness)
- **Statement:** For itemsets X subset Y: support(X) >= support(Y). Hence every frequent set has all its subsets frequent, and pruning below min_sup is lossless.
- **Assumptions:** Support counted over a fixed transaction set.
- **Proof sketch:** The set of transactions containing Y is contained in the set containing X, because Y <= t implies X <= t. Therefore count(Y) <= count(X), and the monotonic enumeration never discards a frequent set.
- **Runtime check:** superset violations below min_sup=0.05: 0 of 2772 candidate pairs; anti-monotonicity violations among 66 item pairs: 0 -> **PASS**

## 6. The stored graph contains no triangles (structural proof)
- **Statement:** No three labels of the schema are pairwise connected by a relationship type, hence no 3-cycle exists in the stored graph; triangle count and clustering coefficient are 0 for every node.
- **Assumptions:** The nine relationship types of TASK 11.3 are the only stored types.
- **Proof sketch:** A triangle in the property graph uses three nodes with pairwise relationships; each relationship carries one of the nine types, so the three labels of its nodes must be pairwise adjacent in the label graph. Checking all 84 label triples shows none is pairwise adjacent (Order's neighbours Customer/OrderItem/Payment/Review are mutually non-adjacent, and the same holds for every other label), so no triangle exists. The label graph itself does contain one long cycle (Order-Customer-Geolocation-Seller-OrderItem), which cannot close into a triangle.
- **Runtime check:** pairwise-adjacent label triples found: 0; label-graph cycles via union-find: 1 long cycle(s), none a triangle -> **PASS**

## 7. Adamic-Adar is bounded by common neighbors / log 2
- **Statement:** AA(i,j) = sum_{z in N(i)^N(j)} 1/log d_z satisfies AA <= CN/log 2 <= min(d_i,d_j)/log 2, since every common neighbor has d_z >= 2.
- **Assumptions:** Simple undirected graph, log base e, degrees >= 2 for shared neighbors.
- **Proof sketch:** Each shared neighbor contributes 1/log d_z <= 1/log 2, so AA <= CN/log 2; and CN(i,j) = |N(i) ^ N(j)| <= min(|N(i)|,|N(j)|) = min(d_i,d_j) because the intersection is a subset of each neighborhood.
- **Runtime check:** violations of AA <= CN/log2: 0; violations of CN <= min(d_i,d_j): 0 -> **PASS**

## 8. Bootstrap p-value estimator is conservative
- **Statement:** With p_hat = (1 + #{stat_null >= stat_obs}) / (b+1) and #exceed ~ Bin(b, p), E[p_hat] = (1 + b p) / (b+1) >= p.
- **Assumptions:** Null statistics are iid with P(stat_null >= stat_obs) = p exactly.
- **Proof sketch:** Linearity of expectation: E[p_hat] = (1 + b p)/(b+1) = p + (1-p)/(b+1), which exceeds p by (1-p)/(b+1) > 0, so the estimator never under-covers and the minimum reportable value is 1/(b+1).
- **Runtime check:** Monte Carlo mean p_hat = 0.03487 vs exact 0.03483 (true p=0.03, minimum possible 1/201=0.00498) -> **PASS**

## 9. Haversine distance = great-circle central angle
- **Statement:** d = 2R arcsin( sqrt( sin^2(dphi/2) + cos phi1 cos phi2 sin^2(dlambda/2) ) ) equals R times the central angle c = arccos(sin phi1 sin phi2 + cos phi1 cos phi2 cos dlambda).
- **Assumptions:** Spherical Earth, radius R, lat/lon in radians.
- **Proof sketch:** The haversine hv(theta) = sin^2(theta/2); substituting into the spherical law of cosines and using sin^2(c/2) = (1 - cos c)/2 gives equality of the two forms; haversine is numerically stable for small distances, the cosine form is not.
- **Runtime check:** random pair: haversine 6254.349484 km vs central-angle 6254.349484 km; antipodes 20015.1 km = pi*R = 20015.1 km -> **PASS**

## 10. Spectral radius bounds the average degree
- **Statement:** For a simple undirected graph, lambda_1(A) >= 2m/n (the average degree), with equality iff the graph is regular.
- **Assumptions:** Adjacency matrix symmetric, nonnegative entries.
- **Proof sketch:** lambda_1 = max_u u^T A u / u^T u; taking u = 1_n gives lambda_1 >= (1^T A 1)/n = 2m/n (Rayleigh quotient and Courant-Fischer). Equality forces the all-ones vector to be a principal eigenvector, i.e. A1 = lambda_1 1: regular.
- **Runtime check:** 50 random graphs: min(lambda_1 - avg_degree) = 1.33e-01 >= 0 -> **PASS**

## 11. Spearman rho is Pearson on mid-ranks
- **Statement:** rho_S = Pearson correlation of the (tie-averaged) ranks of x and y, rho = cov(r_x, r_y) / (sd(r_x) sd(r_y)).
- **Assumptions:** At least one varying variable; mid-ranks for ties.
- **Proof sketch:** Spearman is defined through the mid-rank transform; Pearson is invariant to affine transforms and mid-ranks are a deterministic function of the data, so correlating the mid-ranks reproduces rho_S exactly.
- **Runtime check:** Pearson on mid-ranks = -0.137852740, scipy spearmanr = -0.137852740 -> **PASS**

## 12. Permutation test size under a true null
- **Statement:** If H0 makes the pooled labels exchangeable, the permutation p-value is uniformly distributed; the rejection rate at alpha is <= alpha + small.
- **Assumptions:** Exchangeability under H0; random permutations of the pooled sample.
- **Proof sketch:** Conditional on the pooled values, every split is equiprobable under H0, so the rank of the observed statistic among permutations is uniform on {1,...,B+1}; hence P(p <= alpha) <= alpha + 1/(B+1) in the worst case.
- **Runtime check:** 2000 simulated true-null trials: rejection rate at alpha=0.05 is 0.0495 (<= 0.05 + 1/100 + Monte-Carlo noise) -> **PASS**

## 13. Logistic loss convexity and the unique minimizer
- **Statement:** L(w) = mean[ log(1+e^{z_i}) - y_i z_i ] is convex; grad^2 L = diag(s(1-s)) X^T X / n is PSD, so any stationary point is the global minimizer.
- **Assumptions:** X full column rank; sigmoid s = 1/(1+e^{-z}).
- **Proof sketch:** d2L/dz2 = s(1-s) > 0, so L is convex in z hence in w; the Hessian below is X^T S X/n with S diagonal positive, which is PSD and positive definite when X has full rank, giving a unique finite minimizer with zero gradient.
- **Runtime check:** at optimum: ||grad|| = 1.87e-06, min Hessian eigenvalue = 4.75e-02 >= 0, loss(w*) = 0.4026 -> **PASS**

## 14. Cosine similarity on normalized vectors = dot product
- **Statement:** For x, q nonzero, cos(x,q) = x^T q / (|x||q|); after L2 normalization the cosine ranking equals the inner-product ranking, and the norm carries no ranking information.
- **Assumptions:** All vectors nonzero; normalization is per row.
- **Proof sketch:** Set x~ = x/|x|, q~ = q/|q|; then x~^T q~ = x^T q/(|x||q|) = cos(x,q) by definition, and argmax over a database of cos equals argmax of inner products of normalized rows, preserving ties identically.
- **Runtime check:** top-10 cosine set equals top-10 normalized-dot set: True -> **PASS**

