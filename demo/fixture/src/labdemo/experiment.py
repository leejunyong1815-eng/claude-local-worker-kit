"""Provided experiment harness; workers implement only the two small modules."""
import math
import random
import statistics


def inverse(matrix):
    n = len(matrix)
    rows = [[float(v) for v in row] + [float(i == j) for j in range(n)]
            for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda i: abs(rows[i][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        value = rows[col][col]
        if abs(value) < 1e-14:
            raise ValueError("singular matrix")
        rows[col] = [x / value for x in rows[col]]
        for i in range(n):
            if i != col:
                factor = rows[i][col]
                rows[i] = [x - factor * y for x, y in zip(rows[i], rows[col])]
    return [row[n:] for row in rows]


def matvec(matrix, vector):
    return [math.fsum(a * x for a, x in zip(row, vector)) for row in matrix]


def norm_inf(matrix):
    return max(math.fsum(abs(x) for x in row) for row in matrix)


def relative_residual(matrix, solution, rhs):
    error = math.sqrt(math.fsum((a - b) ** 2 for a, b in zip(matvec(matrix, solution), rhs)))
    return error / math.sqrt(math.fsum(x * x for x in rhs))


def manufactured_case(side):
    """Dirichlet 2-D five-point Poisson stencil with artificial row imbalance.

    b is formed as A @ u_exact: this is a discrete manufactured-solution check,
    not an estimate of continuous-PDE discretization error or a cylinder flow.
    """
    if not isinstance(side, int) or isinstance(side, bool) or not 2 <= side <= 8:
        raise ValueError("demo grid side must be 2..8")
    size = side * side
    matrix = [[0.0] * size for _ in range(size)]
    solution = []
    for y in range(side):
        for x in range(side):
            i = y * side + x
            weight = 10.0 ** (i % 4)
            matrix[i][i] = 4.0 * weight
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < side and 0 <= yy < side:
                    matrix[i][yy * side + xx] = -weight
            solution.append(math.sin(math.pi * (x + 1) / (side + 1)) *
                            math.sin(math.pi * (y + 1) / (side + 1)))
    return matrix, matvec(matrix, solution), solution


def run(row_scale, distribution_fidelity, config):
    if config.get("compute_backend") != "local":
        raise ValueError("this demo only supports local CPU computation")
    sides, shots, seeds = (config[k] for k in ("grid_sides", "shots", "seeds"))
    if (not sides or len(sides) > 3 or not shots or len(shots) > 4 or
            not seeds or len(seeds) > 5 or
            any(not isinstance(s, int) or isinstance(s, bool) or not 1 <= s <= 8192 for s in shots)):
        raise ValueError("experiment exceeds the small demo budget")
    conditioning, sampling, checks = [], [], []
    for side in sides:
        matrix, rhs, exact = manufactured_case(side)
        original = ([row[:] for row in matrix], rhs[:])
        scaled, scaled_rhs = row_scale(matrix, rhs)
        if (matrix, rhs) != original:
            raise ValueError("row_scale mutated the input")
        raw_inv, scaled_inv = inverse(matrix), inverse(scaled)
        raw_solution = matvec(raw_inv, rhs)
        scaled_solution = matvec(scaled_inv, scaled_rhs)
        raw_cond = norm_inf(matrix) * norm_inf(raw_inv)
        scaled_cond = norm_inf(scaled) * norm_inf(scaled_inv)
        residual = relative_residual(matrix, scaled_solution, rhs)
        error = max(abs(a - b) for a, b in zip(scaled_solution, exact))
        checks.extend([
            {"name": f"N={side}: residual", "value": residual, "limit": 1e-10, "passed": residual <= 1e-10},
            {"name": f"N={side}: manufactured solution", "value": error, "limit": 1e-10, "passed": error <= 1e-10},
            {"name": f"N={side}: equivalent systems", "value": max(abs(a - b) for a, b in zip(raw_solution, scaled_solution)),
             "limit": 1e-10, "passed": max(abs(a - b) for a, b in zip(raw_solution, scaled_solution)) <= 1e-10},
        ])
        conditioning.append(dict(grid_side=side, unknowns=side * side, condition_norm="infinity",
                                 raw_condition=raw_cond, scaled_condition=scaled_cond,
                                 condition_ratio=raw_cond / scaled_cond, residual=residual, max_solution_error=error))
        total = math.fsum(x * x for x in exact)
        probabilities = [x * x / total for x in exact]
        for count in shots:
            values = []
            for seed in seeds:
                rng = random.Random(seed + side * 10000 + count)
                samples = [0] * len(probabilities)
                for index in rng.choices(range(len(samples)), weights=probabilities, k=count):
                    samples[index] += 1
                value = distribution_fidelity(samples, probabilities)
                if not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError("invalid distribution fidelity")
                values.append(value)
            sampling.append(dict(grid_side=side, shots=count, seeds=seeds, values=values,
                                 mean=statistics.mean(values),
                                 sample_std=statistics.stdev(values) if len(values) > 1 else 0.0))
    return dict(conditioning=conditioning, sampling=sampling, checks=checks,
                scientific_scope="synthetic discrete Poisson + classical multinomial sampling",
                fidelity_quantity="classical_distribution_fidelity_not_quantum_state_fidelity")
