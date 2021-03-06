# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.
"""
Readout error class for Qiskit Aer noise model.
"""

import copy

import numpy as np
from numpy.linalg import norm

from qiskit.quantum_info.operators.predicates import is_identity_matrix
from qiskit.quantum_info.operators.predicates import ATOL_DEFAULT, RTOL_DEFAULT

from ..noiseerror import NoiseError
from .errorutils import qubits_from_mat


class ReadoutError:
    """
    Readout error class for Qiskit Aer noise model.
    """

    ATOL = ATOL_DEFAULT
    RTOL = RTOL_DEFAULT
    MAX_TOL = 1e-4

    def __init__(self, probabilities, atol=ATOL_DEFAULT):
        """
        Create a readout error for a noise model.

        Args:
            probabilities (matrix): List of outcome assignment probabilities.
            atol (double): Threshold for checking probabilities are normalized
                           [Default: 1e-8]

        Additional Information:
            For an N-qubit readout error probabilites are entered as vectors:
                probabilities[j] = [P(j|0), P(j|1), ..., P(j|2 ** N - 1)]
            where P(j|m) is the probability of recording a measurement outcome
            of `m` as the value `j`. Where `j` and `m` are integer
            representations of bitstrings.

            Example: 1-qubit
                probabilities[0] = [P("0"|"0"), P("1"|"0")
                probabilities[1] = [P("0"|"1"), P("1"|"1")

            Example: 2-qubit
                probabilities[0] = [P("00"|"00"), P("01"|"00"), P("10"|"00"), P("11"|"00")]
                probabilities[1] = [P("00"|"01"), P("01"|"01"), P("10"|"01"), P("11"|"01")]
                probabilities[1] = [P("00"|"10"), P("01"|"10"), P("10"|"10"), P("11"|"10")]
                probabilities[1] = [P("00"|"11"), P("01"|"11"), P("10"|"11"), P("11"|"11")]
        """
        self._check_probabilities(probabilities, atol)
        self._probabilities = np.array(probabilities, dtype=float)
        self._number_of_qubits = qubits_from_mat(probabilities)

    def __repr__(self):
        """Display ReadoutError."""
        return "ReadoutError({})".format(self._probabilities)

    def __str__(self):
        """Print error information."""
        output = "ReadoutError on {} qubits.".format(self._number_of_qubits) + \
                 " Assignment probabilities:"
        for j, vec in enumerate(self._probabilities):
            output += "\n P(j|{0}) =  {1}".format(j, vec)
        return output

    def copy(self):
        """Make a copy of current ReadoutError."""
        # pylint: disable=no-value-for-parameter
        # The constructor of subclasses from raw data should be a copy
        return copy.deepcopy(self)

    @property
    def number_of_qubits(self):
        """Return the number of qubits for the error."""
        return self._number_of_qubits

    @property
    def probabilities(self):
        """Return the readout error probabilities matrix."""
        return self._probabilities

    @property
    def atol(self):
        """The absolute tolerence parameter for float comparisons."""
        return ReadoutError.ATOL

    @atol.setter
    def atol(self, atol):
        """Set the absolute tolerence parameter for float comparisons."""
        max_tol = ReadoutError.MAX_TOL
        if atol < 0:
            raise NoiseError("Invalid atol: must be non-negative.")
        if atol > max_tol:
            raise NoiseError(
                "Invalid atol: must be less than {}.".format(max_tol))
        ReadoutError.ATOL = atol

    @property
    def rtol(self):
        """The relative tolerence parameter for float comparisons."""
        return ReadoutError.RTOL

    @rtol.setter
    def rtol(self, rtol):
        """Set the relative tolerence parameter for float comparisons."""
        max_tol = ReadoutError.MAX_TOL
        if rtol < 0:
            raise NoiseError("Invalid rtol: must be non-negative.")
        if rtol > max_tol:
            raise NoiseError(
                "Invalid rtol: must be less than {}.".format(max_tol))
        ReadoutError.RTOL = rtol

    def ideal(self):
        """Return True if current error object is an identity"""
        iden = np.eye(2**self.number_of_qubits)
        delta = round(norm(np.array(self.probabilities) - iden), 12)
        if delta == 0:
            return True
        return False

    def as_dict(self):
        """Return the current error as a dictionary."""
        error = {
            "type": "roerror",
            "operations": ["measure"],
            "probabilities": self._probabilities.tolist()
        }
        return error

    def compose(self, other, front=False):
        """Return the composition readout error self∘other.

        Args:
            other (ReadoutError): a readout error.
            front (bool): If False compose in standard order other(self(input))
                          otherwise compose in reverse order self(other(input))
                          [default: False]

        Returns:
            ReadoutError: The composition readout error.

        Raises:
            NoiseError: if other is not a ReadoutError or has incompatible
            dimensions.
        """
        if not isinstance(other, ReadoutError):
            other = ReadoutError(other)
        if self.number_of_qubits != other.number_of_qubits:
            raise NoiseError("other must have same number of qubits.")
        if front:
            probs = np.dot(self._probabilities, other._probabilities)
        else:
            probs = np.dot(other._probabilities, self._probabilities)
        return ReadoutError(probs)

    def power(self, n):
        """Return the compose of the readout error with itself n times.

        Args:
            n (int): the number of times to compose with self (n>0).

        Returns:
            ReadoutError: the n-times composition channel.

        Raises:
            NoiseError: if the power is not a positive integer.
        """
        if not isinstance(n, int) or n < 1:
            raise NoiseError("Can only power with positive integer powers.")
        ret = self.copy()
        for _ in range(1, n):
            ret = ret.compose(self)
        return ret

    def tensor(self, other):
        """Return the tensor product readout error self ⊗ other.

        Args:
            other (ReadoutError): a readout error.

        Returns:
            ReadoutError: the tensor product readout error self ⊗ other.

        Raises:
            NoiseError: if other is not a ReadoutError.
        """
        return self._tensor_product(other, reverse=False)

    def expand(self, other):
        """Return the tensor product readout error self ⊗ other.

        Args:
            other (ReadoutError): a readout error.

        Returns:
            ReadoutError: the tensor product readout error other ⊗ self.

        Raises:
            NoiseError: if other is not a ReadoutError.
        """
        return self._tensor_product(other, reverse=True)

    @staticmethod
    def _check_probabilities(probabilities, threshold):
        """Check probabilities are valid."""
        if len(probabilities) == 0:
            raise NoiseError("Input probabilities: empty.")
        num_outcomes = len(probabilities[0])
        num_qubits = int(np.log2(num_outcomes))
        if 2**num_qubits != num_outcomes:
            raise NoiseError("Invalid probabilities: length "
                             "{} != 2**{}".format(num_outcomes, num_qubits))
        if len(probabilities) != num_outcomes:
            raise NoiseError("Invalid probabilities.")
        for vec in probabilities:
            arr = np.array(vec)
            if len(arr) != num_outcomes:
                raise NoiseError(
                    "Invalid probabilities: vectors are different lengths.")
            if abs(sum(arr) - 1) > threshold:
                raise NoiseError("Invalid probabilities: sum({})= {} "
                                 "is not 1.".format(vec, sum(arr)))
            if len(arr[arr < 0]) > 0:
                raise NoiseError(
                    "Invalid probabilities: {} "
                    "contains a negative probability.".format(vec))

    def _tensor_product(self, other, reverse=False):
        """Return the tensor product readout error.

        Args:
            other (ReadoutError): a readout error.
            reverse (bool): If False return self ⊗ other, if True return
                            if True return (other ⊗ self) [Default: False
        Returns:
            ReadoutError: the tensor product readout error.
        """
        if not isinstance(other, ReadoutError):
            other = ReadoutError(other)
        if reverse:
            probs = np.kron(other._probabilities, self._probabilities)
        else:
            probs = np.kron(self._probabilities, other._probabilities)
        return ReadoutError(probs)
