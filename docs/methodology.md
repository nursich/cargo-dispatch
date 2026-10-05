# Methodology

## Problem statement

Let *R* = {r₁ … rₙ} be cargo requests and *C* = {c₁ … cₘ} carriers available in one
dispatch round. Each carrier can take at most one request and each request needs at most
one carrier. The task is to choose a set of pairs (a *matching*) that maximises the total
priority-weighted quality of service.

## Feasibility

Pair *(i, j)* is feasible if

- `weight_i ≤ capacity_j`, and
- `vehicle_type_j ∈ allowed(cargo_type_i)`:

| cargo type | allowed vehicles |
|---|---|
| general | tent, refrigerator, flatbed |
| perishable | refrigerator |
| liquid | tanker |
| oversized | flatbed |

## Cost

`empty_km_ij` is the road distance from the carrier's position to the pick-up point and
`loaded_km_i` the distance from pick-up to drop-off. Road distance is approximated as the
haversine distance × 1.25 (a typical detour factor for intercity roads).

`cost_ij = (empty_km_ij + loaded_km_i) · rate_per_km_j`  [KZT]

## Score

With normalised weights `w_cost + w_rel + w_rat = 1` (defaults 0.5 / 0.3 / 0.2):

`s_ij = w_cost · (1 − cost_ij / max_feasible_cost) + w_rel · on_time_j + w_rat · rating_j / 5`

Each term lies in [0, 1], so `s_ij ∈ [0, 1]`. The cost term is normalised by the most
expensive feasible pair in the current round, which keeps the three criteria comparable.

## Objective

`maximise Σ_(i,j)∈M  p_i · s_ij`, with `p_i` = 1.0, 1.5, 2.0 for priority 1, 2, 3.

## Algorithms

**Greedy.** Sort requests by priority (descending), then by weight (descending, because
heavy loads have fewer feasible carriers). For each request take the free feasible carrier
with the highest score. Complexity O(n·m). It can make a locally good choice that blocks a
better global solution (see `test_optimal_assigns_more_than_greedy_when_greedy_blocks`).

**Optimal.** The problem is a rectangular linear assignment problem. The benefit matrix
`B_ij = p_i · s_ij` (or −10⁹ for infeasible pairs) is passed to
`scipy.optimize.linear_sum_assignment(B, maximize=True)`, which implements a modified
Jonker–Volgenant / Hungarian algorithm with O(n³) worst-case complexity. Pairs that were
matched only because the matrix had to be filled (infeasible ones) are dropped, and the
corresponding requests are reported as unassigned.

## Limitations and future work

- One request per carrier per round; multi-stop routing (VRP) is out of scope.
- Straight-line distance × factor instead of a real road graph (OSRM could be plugged in).
- Static weights; they could be learned from historical dispatcher decisions.
- Time windows and driver working hours are not modelled.
