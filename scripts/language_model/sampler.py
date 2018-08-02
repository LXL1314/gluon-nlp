# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Log Uniform Candidate Sampler"""

import math
import numpy as np
import log_uniform
from mxnet import ndarray
from gluonnlp.data import CandidateSampler

class LogUniformSampler(CandidateSampler):
    """Draw random samples from an approximately log-uniform or Zipfian distribution.

    This operation randomly samples *num_sampled* candidates the range of integers [0, range_max).
    The elements of sampled_candidates are drawn without replacement from the base distribution.

    The base distribution for this operator is an approximately log-uniform or Zipfian distribution:

    P(class) = (log(class + 2) - log(class + 1)) / log(range_max + 1)

    This sampler is useful when the true classes approximately follow such a distribution.

    For example, if the classes represent words in a lexicon sorted in decreasing order of
    frequency. If your classes are not ordered by decreasing frequency, do not use this op.

    Additionaly, it also returns the number of times each of the
    true classes and the sampled classes is expected to occur.

    Parameters
    ----------
    num_sampled: int
        The number of classes to randomly sample.
    range_max: int
        The number of possible classes.
    seed: int
        The random seed.
    """
    def __init__(self, range_max, num_sampled, dtype=None, seed=0):
        self._num_sampled = num_sampled
        self._log_range = math.log(range_max + 1)
        self._csampler = log_uniform.LogUniformSampler(range_max, seed)
        self._dtype = np.float32 if dtype is None else dtype

    def _prob_helper(self, num_tries, num_sampled, prob):
        if num_tries == num_sampled:
            return prob * num_sampled
        return (num_tries * (-prob).log1p()).expm1() * -1

    def __call__(self, true_classes):
        """Draw samples from log uniform distribution and returns sampled candidates,
        expected count for true classes and sampled classes.

        Parameters
        ----------
        true_classes: NDArray
            The true classes.

        Returns
        -------
        samples: NDArray
            The sampled candidate classes.
        expected_count_true: NDArray
            The expected count for true classes in the same shape as `true_classes`.
        expected_count_sample: NDArray
            The expected count for sampled candidates.
        """
        num_sampled = self._num_sampled
        ctx = true_classes.context
        num_tries = 0
        log_range = self._log_range
        sampled_classes, num_tries = self._csampler.sample_unique(num_sampled)
        # expected count for true classes
        true_cls = true_classes.as_in_context(ctx).astype('float64')
        prob_true = ((true_cls + 2.0) / (true_cls + 1.0)).log() / log_range
        count_true = self._prob_helper(num_tries, num_sampled, prob_true)
        # expected count for sampled classes
        sampled_classes = ndarray.array(sampled_classes, ctx=ctx, dtype='int64')
        sampled_cls_fp64 = sampled_classes.astype('float64')
        prob_sampled = ((sampled_cls_fp64 + 2.0) / (sampled_cls_fp64 + 1.0)).log() / log_range
        count_sampled = self._prob_helper(num_tries, num_sampled, prob_sampled)
        # convert to dtype
        sampled_classes = sampled_classes.astype(self._dtype, copy=False)
        count_true = count_true.astype(self._dtype, copy=False)
        count_sampled = count_sampled.astype(self._dtype, copy=False)
        return sampled_classes, count_true, count_sampled