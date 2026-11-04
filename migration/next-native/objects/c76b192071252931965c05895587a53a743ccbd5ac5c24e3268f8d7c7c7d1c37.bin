# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. elkjs0.12.1 Pair, lines73790-73799.
# CT source review HOST16/V/component-transformer-controller-source-review-01.
"""Combine already requested field codes without allocating a Pair identity."""


def pair_hash_codes(first, second):
    code = ((first & 65535) ^ ((second >> 16) & 65535)) | ((first & -65536) ^ ((second & 65535) << 16))
    return (code + 2147483648) % 4294967296 - 2147483648
