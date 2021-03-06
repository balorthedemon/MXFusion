import pytest
import mxnet as mx
import numpy as np
from mxfusion.util.special import log_determinant, log_multivariate_gamma
from sklearn.datasets import make_spd_matrix
from itertools import product
from scipy.special import multigammaln


# @pytest.mark.usefixtures("set_seed")
class TestSpecialFunctions:
    """
    Tests special functions.
    Note we're currently using the seed as a parameter here rather than the decorator so as to have multiple seeds
    """

    @pytest.mark.parametrize("n_dim, random_state", list(product((10, 100, 1000), range(1, 4))))
    def test_log_determinant(self, n_dim, random_state):
        A = make_spd_matrix(n_dim=n_dim, random_state=random_state)
        assert all(np.linalg.eigvals(A) > 0)

        a = mx.nd.array(A)
        b = log_determinant(a, mx.nd)

        mx_logdet = b.asnumpy()
        np_logdet = np.linalg.slogdet(A)[1]

        # Alternative versions of the numpy function (the above is more robust):
        # np.log(np.linalg.eigvals(A))
        # 2 * sum(np.log(np.diag(np.linalg.cholesky(A))))

        assert abs(mx_logdet - np_logdet) < 1e-5 * n_dim

    @pytest.mark.parametrize("n_data_points, n_dim, random_state", list(product((4, ), (1, 10, 100), range(1, 4))))
    def test_log_mv_gamma(self, n_data_points, n_dim, random_state):
        np.random.seed(random_state)
        x = np.random.rand(n_data_points) + n_dim
        a = mx.nd.array(x)
        b = log_multivariate_gamma(a, n_dim, mx.nd)

        mx_val = b.asnumpy()
        sp_val = multigammaln(x, n_dim)
        assert np.allclose(mx_val, sp_val, atol=1e-3 * n_dim)

    @pytest.mark.parametrize("n_samples, n_data_points, n_dim, random_state", [(5, 4, 10, 0)])
    def test_log_mv_gamma_broadcast(self, n_samples, n_data_points, n_dim, random_state):
        np.random.seed(random_state)
        x = np.random.rand(n_samples, n_data_points) + n_dim
        a = mx.nd.array(x)
        b = log_multivariate_gamma(a, n_dim, mx.nd)

        mx_val = b.asnumpy()
        sp_val = multigammaln(x, n_dim)
        assert np.allclose(mx_val, sp_val, atol=1e-3 * n_dim)
