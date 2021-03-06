import pytest
import mxnet as mx
import numpy as np
from mxfusion.components.variables.runtime_variable import add_sample_dimension, is_sampled_array, get_num_samples
from mxfusion.components.distributions import Beta
from mxfusion.util.testutils import numpy_array_reshape
from mxfusion.util.testutils import MockMXNetRandomGenerator

from scipy.stats import beta


@pytest.mark.usefixtures("set_seed")
class TestBetaDistribution(object):

    @pytest.mark.parametrize("dtype, a, a_is_samples, b, b_is_samples, rv, rv_is_samples, num_samples", [
        (np.float64, np.random.uniform(0.5, 2, size=(5, 2)), True, np.random.uniform(0.5, 2, size=(2,)), False, np.random.beta(1, 1, size=(5, 3, 2)), True, 5),
        (np.float64, np.random.uniform(0.5, 2, size=(5, 2)), True, np.random.uniform(0.5, 2, size=(2,)), False, np.random.beta(1, 1, size=(5, 3, 2)), False, 5),
        (np.float64, np.random.uniform(0.5, 2, size=(2,)), False, np.random.uniform(0.5, 2, size=(2,)), False, np.random.beta(1, 1, size=(5, 3, 2)), False, 5),
        (np.float64, np.random.uniform(0.5, 2, size=(5, 2)), True, np.random.uniform(0.5, 2, size=(5, 3, 2)), True, np.random.beta(1, 1, size=(5, 3, 2)), True, 5),
        (np.float32, np.random.uniform(0.5, 2, size=(5, 2)), True, np.random.uniform(0.5, 2, size=(2,)), False, np.random.beta(1, 1, size=(5, 3, 2)), True, 5),
        ])
    def test_log_pdf(self, dtype, a, a_is_samples, b, b_is_samples, rv, rv_is_samples, num_samples):

        is_samples_any = any([a_is_samples, b_is_samples, rv_is_samples])
        rv_shape = rv.shape[1:] if rv_is_samples else rv.shape
        n_dim = 1 + len(rv.shape) if is_samples_any and not rv_is_samples else len(rv.shape)
        a_np = numpy_array_reshape(a, a_is_samples, n_dim)
        b_np = numpy_array_reshape(b, b_is_samples, n_dim)
        rv_np = numpy_array_reshape(rv, rv_is_samples, n_dim)

        log_pdf_np = beta.logpdf(rv_np, a_np, b_np)

        var = Beta.define_variable(shape=rv_shape, dtype=dtype).factor
        a_mx = mx.nd.array(a, dtype=dtype)
        if not a_is_samples:
            a_mx = add_sample_dimension(mx.nd, a_mx)
        b_mx = mx.nd.array(b, dtype=dtype)
        if not b_is_samples:
            b_mx = add_sample_dimension(mx.nd, b_mx)
        rv_mx = mx.nd.array(rv, dtype=dtype)
        if not rv_is_samples:
            rv_mx = add_sample_dimension(mx.nd, rv_mx)
        variables = {var.a.uuid: a_mx, var.b.uuid: b_mx, var.random_variable.uuid: rv_mx}
        log_pdf_rt = var.log_pdf(F=mx.nd, variables=variables)

        assert np.issubdtype(log_pdf_rt.dtype, dtype)
        assert is_sampled_array(mx.nd, log_pdf_rt) == is_samples_any
        if is_samples_any:
            assert get_num_samples(mx.nd, log_pdf_rt) == num_samples
        if np.issubdtype(dtype, np.float64):
            rtol, atol = 1e-7, 1e-10
        else:
            rtol, atol = 1e-4, 1e-5
        assert np.allclose(log_pdf_np, log_pdf_rt.asnumpy(), rtol=rtol, atol=atol)

    @pytest.mark.parametrize(
        "dtype, a_shape, a_is_samples, b_shape, b_is_samples, rv_shape, num_samples", [
            (np.float64, (int(1e4), 2), True, (2,), False, (3, 2), int(1e4)),
            # (np.float64, (2,), False, (int(1e4), 2), True, (3, 2), int(1e4)),
            # (np.float64, (2,), False, (2,), False, (3, 2), int(1e7)),
            # (np.float64, (int(1e5), 2), True, (int(1e5), 3, 2), True, (3, 2), int(1e5)),
            # (np.float32, (int(1e4), 2), True, (2,), False, (3, 2), int(1e4)),
        ])
    def test_draw_samples(self, dtype, a_shape, a_is_samples, b_shape, b_is_samples, rv_shape, num_samples):
        # Note: Tests above have been commented as they are very slow to run.
        # Note: Moved random number generation to here as the seed wasn't set if used above
        a = np.random.uniform(0.5, 2, size=a_shape)
        b = np.random.uniform(0.5, 2, size=b_shape)

        n_dim = 1 + len(rv_shape)
        a_np = numpy_array_reshape(a, a_is_samples, n_dim)
        b_np = numpy_array_reshape(b, b_is_samples, n_dim)

        rv_samples_np = np.random.beta(a_np, b_np, size=(num_samples,) + rv_shape)

        var = Beta.define_variable(shape=rv_shape, dtype=dtype, rand_gen=None).factor

        a_mx = mx.nd.array(a, dtype=dtype)
        if not a_is_samples:
            a_mx = add_sample_dimension(mx.nd, a_mx)

        b_mx = mx.nd.array(b, dtype=dtype)
        if not b_is_samples:
            b_mx = add_sample_dimension(mx.nd, b_mx)

        variables = {var.a.uuid: a_mx, var.b.uuid: b_mx}
        rv_samples_rt = var.draw_samples(F=mx.nd, variables=variables, num_samples=num_samples)

        assert np.issubdtype(rv_samples_rt.dtype, dtype)
        assert is_sampled_array(mx.nd, rv_samples_rt)
        assert get_num_samples(mx.nd, rv_samples_rt) == num_samples

        rtol, atol = 1e-1, 1e-1

        from itertools import product
        fits_np = [beta.fit(rv_samples_np[:, i, j])[0:2] for i, j in (product(*map(range, rv_shape)))]
        fits_rt = [beta.fit(rv_samples_rt.asnumpy()[:, i, j])[0:2] for i, j in (product(*map(range, rv_shape)))]

        assert np.allclose(fits_np, fits_rt, rtol=rtol, atol=atol)
