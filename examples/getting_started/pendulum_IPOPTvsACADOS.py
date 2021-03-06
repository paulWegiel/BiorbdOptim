import biorbd
import numpy as np
from time import time
from biorbd_optim import (
    OptimalControlProgram,
    ObjectiveList,
    Objective,
    DynamicsTypeList,
    DynamicsType,
    BoundsList,
    QAndQDotBounds,
    InitialConditionsList,
    ShowResult,
    Instant,
    Solver,
)


def prepare_ocp(biorbd_model_path, final_time, number_shooting_points, nb_threads, use_SX=False):
    # --- Options --- #
    biorbd_model = biorbd.Model(biorbd_model_path)
    torque_min, torque_max, torque_init = -100, 100, 0
    n_q = biorbd_model.nbQ()
    n_qdot = biorbd_model.nbQdot()
    n_tau = biorbd_model.nbGeneralizedTorque()
    data_to_track = np.zeros((number_shooting_points + 1, n_q + n_qdot))
    data_to_track[:, 1] = 3.14
    # Add objective functions
    objective_functions = ObjectiveList()
    objective_functions.add(Objective.Lagrange.MINIMIZE_TORQUE, weight=100.0)
    objective_functions.add(Objective.Lagrange.MINIMIZE_STATE, weight=1.0)
    objective_functions.add(
        Objective.Mayer.MINIMIZE_STATE, weight=50000.0, target=data_to_track.T, instant=Instant.END,
    )

    # Dynamics
    dynamics = DynamicsTypeList()
    dynamics.add(DynamicsType.TORQUE_DRIVEN)

    # Path constraint
    x_bounds = BoundsList()
    x_bounds.add(QAndQDotBounds(biorbd_model))
    x_bounds[0].min[:, 0] = 0
    x_bounds[0].max[:, 0] = 0

    # Initial guess
    x_init = InitialConditionsList()
    x_init.add([0] * (n_q + n_qdot))

    # Define control path constraint
    u_bounds = BoundsList()
    u_bounds.add(
        [[torque_min] * n_tau, [torque_max] * n_tau,]
    )
    u_bounds[0].min[n_tau - 1, :] = 0
    u_bounds[0].max[n_tau - 1, :] = 0

    u_init = InitialConditionsList()
    u_init.add([torque_init] * n_tau)

    # ------------- #

    return OptimalControlProgram(
        biorbd_model,
        dynamics,
        number_shooting_points,
        final_time,
        x_init,
        u_init,
        x_bounds,
        u_bounds,
        objective_functions,
        nb_threads=nb_threads,
        use_SX=use_SX,
    )


if __name__ == "__main__":
    ocp = prepare_ocp(
        biorbd_model_path="pendulum.bioMod", final_time=3, number_shooting_points=41, nb_threads=4, use_SX=True
    )

    # --- Solve the program --- #
    tic = time()
    sol_ip = ocp.solve(solver=Solver.IPOPT)
    toc = time() - tic
    print(f"Time to solve with IPOPT: {toc}sec")
    tic = time()
    sol_ac = ocp.solve(solver=Solver.ACADOS)
    toc = time() - tic
    print(f"Time to solve with ACADOS: {toc}sec")

    # --- Show results --- #
    result_ip = ShowResult(ocp, sol_ip)
    result_ac = ShowResult(ocp, sol_ac)
    result_ip.graphs()
    result_ac.graphs()
    result_ip.animate()
    result_ac.animate()
