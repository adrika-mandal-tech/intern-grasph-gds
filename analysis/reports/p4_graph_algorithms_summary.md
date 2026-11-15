# Phase 4 — graph algorithms on source-derived projections

Read-only analysis; no writes to Grasph. Projections from task03 (name, nodes, edges in each section).

## seller_shared_products: 3095 nodes, 1061 edges
- components: 2423, isolates: 2309, giant: 390 (12.6%)
- mean degree 0.686, max 27, k-core max 7, giant ASPL 6.5448, diameter 18
- PageRank vs degree Spearman rho=0.9881 (p=0); top-10 identical to plain degree: False
- betweenness top-5 (unweighted): ['b2ba3715d723d245138f291a6fe42594', '612170e34b97004b3ba37eae81836b4c', '8444e55c1f13cd5c179851e5ca5ebd00', '620c87c171fb2a6dd6e8bb4dec959fc6', '46dc3b2cc0980fb8ec44634e21d2718e']; weighted vs unweighted rho=0.9246

## seller_shared_categories: 3095 nodes, 724613 edges
- components: 1, isolates: 0, giant: 3095 (100.0%)
- mean degree 468.247, max 2686, k-core max 491, giant ASPL 1.8675, diameter 3
- Louvain modularity 0.3553–0.3585 over 10 seeds, communities 6–7, NMI vs seed0 0.698–0.825
- null (degree-preserving rewiring, 20 reps): modularity 0.0292 ± 0.0007, permutation p=0.0476
- PageRank vs degree Spearman rho=0.9853 (p=0); top-10 identical to plain degree: False

## seller_co_order: 3095 nodes, 1151 edges
- components: 2343, isolates: 2270, giant: 651 (21.0%)
- mean degree 0.744, max 42, k-core max 5, giant ASPL 5.2117, diameter 13
- PageRank vs degree Spearman rho=0.9915 (p=0); top-10 identical to plain degree: False
- betweenness top-5 (unweighted): ['1f50f920176fa81dab994f9023523100', '4a3ca9315b744ce9f8e9374361493884', 'da8622b14eb17ae2831f4ac5b9dab84a', '1900267e848ceeba8fa32d80c1a5f5a8', '6560211a19b47992c3666cc44a7e94c0']; weighted vs unweighted rho=0.9843

## product_bought_together: 32951 nodes, 4058 edges
- components: 29718, isolates: 28066, giant: 398 (1.2%)
- mean degree 0.246, max 23, k-core max 7, giant ASPL 10.1282, diameter 29
- PageRank vs degree Spearman rho=0.9948 (p=0); top-10 identical to plain degree: False

## category_shared_sellers: 74 nodes, 1435 edges
- components: 1, isolates: 0, giant: 74 (100.0%)
- mean degree 38.784, max 70, k-core max 34, giant ASPL 1.4691, diameter 3
- Louvain modularity 0.0975–0.1 over 10 seeds, communities 4–5, NMI vs seed0 0.871–1.0
- null (degree-preserving rewiring, 20 reps): modularity 0.0529 ± 0.0044, permutation p=0.0476
- PageRank vs degree Spearman rho=0.9841 (p=7.8e-56); top-10 identical to plain degree: False
- betweenness top-5 (unweighted): ['utilidades_domesticas', 'moveis_decoracao', 'informatica_acessorios', 'automotivo', 'esporte_lazer']; weighted vs unweighted rho=0.132

