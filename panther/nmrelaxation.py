
import numpy as np

from .vibrations import harmonic_vibrational_analysis


def nmoptimize(atoms, hessian, calc, proj_translations=True,
               proj_rotations=True, gtol=1.0e-5):
    '''
    Relax the strcture using normal mode displacements

    Parameters
    ----------
    atoms : ase.Atoms
    hessian : array_like
        Hessian matrix
    calc : ase.Calculator

    Notes
    -----

    .. see-also::

    '''

    natoms = atoms.get_number_of_atoms()
    ndof = 3 * natoms
    masses = atoms.get_masses()
    pos = atoms.get_positions()
    coords = pos.ravel()

    # matrix with inverse square roots of masses on diagonal
    M_invsqrt = np.zeros((ndof, ndof), dtype=float)
    np.fill_diagonal(M_invsqrt, np.repeat(1.0 / np.sqrt(masses * prm), 3))

    # calculate hessian eigenvalues and eigenvectors
    evals, evecs = harmonic_vibrational_analysis(hessian, atoms,
                                           proj_translations=proj_translations,
                                           proj_rotations=proj_rotations,
                                           ascomplex=False)

    mwevecs = np.dot(M_invsqrt, evecs)

    coords_old = coords.copy()

    # run the job for the initial structure
    atoms.set_calculator(calc)

    # get forces after run
    grad = atoms.get_forces().ravel()

    grad_old = grad.copy()

    grad_nm = np.dot(mwevecs.T, grad)

    step_nm = -2.0 * grad_nm / (evals * (1.0 + np.sqrt(1.0 + (4.0 * grad_nm**2) / evals**2)))

    step_cart = np.dot(mwevecs, step_nm)

    coords = coords_old + step_cart

    not_converged = True
    iteration = 0
    while not_converged:
        print(' iteration {0:d} '.format(iteration).center(80, '='))

        delta_coord = coords - coords_old

        atoms.set_positions(coords.reshape(natoms, 3))

        coords_old = coords.copy()
        grad = atoms.get_forces().ravel()

        delta_grad = grad - grad_old

        update_hessian(grad, grad_old, step_cart, hessian)

        grad_old = grad.copy()

        # calculate hessian eigenvalues and eigenvectors
        evals, evecs = harmonic_vibrational_analysis(hessian, atoms,
                                               proj_translations=proj_translations,
                                               proj_rotations=proj_rotations,
                                               ascomplex=False)
        mwevecs = np.dot(M_invsqrt, evecs)
        grad_nm = np.dot(mwevecs.T, grad)

        gmax = np.max(np.abs(grad_nm))

        if gmax < gtol:
            evals, evecs = harmonic_vibrational_analysis(hessian, atoms,
                                               proj_translations=proj_translations,
                                               proj_rotations=proj_rotations,
                                               ascomplex=False)
            np.save('hessian_evalues', evals)
            np.save('hessian_evectors', evecs)

        step_nm = -2.0 * grad_nm / (evals * (1.0 + np.sqrt(1.0 + (4.0 * grad_nm**2) / evals**2)))
        step_cart = np.dot(mwevecs, step_nm)
        coords = coords_old + step_cart

        iteration += 1


def update_hessian(grad, grad_old, dx, hessian, update='BFGS'):
    '''
    Perform hessian update

    Parameters
    ----------
    grad : array_like (N,)
    grad_old : array_like (N,)
    dx : array_like (N,)
    hessian : array_like (N, N)
    update : str
        Name of the hessian update to perform

    Returns
    -------
    uhessian : array_like
        Update hessian matrix
    '''

    if update != 'BFGS':
        raise NotImplementedError

    dg = grad - grad_old

    a = np.dot(dx, dg)
    hdx = np.dot(hessian, dx)

    b = np.dot(dx, hdx)

    return hessian + np.outer(dg, dg) / a - np.outer(hdx, hdx) / b
