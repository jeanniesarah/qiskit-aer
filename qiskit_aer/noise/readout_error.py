# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Readout error class for Qiskit Aer noise model.
"""

from numpy import array, log2

from .noise_utils import qubits_from_mat
from .aernoiseerror import AerNoiseError


class ReadoutError:
    """
    Readout error class for Qiskit Aer noise model.
    """

    def __init__(self, probabilities):
        """
        Create a readout error for a noise model.

        Args:
            probabilities (array like): List of outcome assignment probabilities.

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
        self._check_probabilities(probabilities, 1e-10)
        self._probabilities = probabilities
        self._number_of_qubits = qubits_from_mat(probabilities)

    @property
    def number_of_qubits(self):
        """Return the number of qubits for the error."""
        return self._number_of_qubits

    @property
    def probabilities(self):
        """Return the readout error probabilities matrix."""
        return self._probabilities

    def as_dict(self):
        """Return the current error as a dictionary."""
        error = {"type": "roerror",
                 "operations": ["measure"],
                 "probabilities": self._probabilities}
        return error

    @staticmethod
    def _check_probabilities(probabilities, threshold):
        """Check probabilities are valid."""
        if len(probabilities) == 0:
            raise AerNoiseError("Input probabilities: empty.")
        num_outcomes = len(probabilities[0])
        num_qubits = int(log2(num_outcomes))
        if 2 ** num_qubits != num_outcomes:
            raise AerNoiseError("Invalid probabilities: length" +
                                "{} != 2**{}".format(num_outcomes, num_qubits))
        if len(probabilities) != num_outcomes:
            raise AerNoiseError("Invalid probabilities.")
        for vec in probabilities:
            arr = array(vec)
            if len(arr) != num_outcomes:
                raise AerNoiseError("Invalid probabilities: vectors are different lengths.")
            if abs(sum(arr) - 1) > threshold:
                raise AerNoiseError("Invalid probabilities: sum({})".format(vec) +
                                    " = {} is not 1.".format(sum(arr)))
            if len(arr[arr < 0]) > 0:
                raise AerNoiseError("Invalid probabilities: {}".format(vec) +
                                    " contains a negative probability.")

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