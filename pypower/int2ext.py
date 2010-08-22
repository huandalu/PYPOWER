# Copyright (C) 1996-2010 Power System Engineering Research Center
# Copyright (C) 2010 Richard Lincoln <r.w.lincoln@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www["A"]pache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from bus_idx import PQ, PV, REF, NONE, BUS_I
from gen_idx import GEN_BUS
from brch_idx import F_BUS, T_BUS
from idx_area import AREA_I, PRICE_REF_BUS

from get_reorder import get_reorder
from set_reorder import set_reorder
from run_userfcn import run_userfcn

logger = logging.getLogger(__name__)

def int2ext(i2e, bus, gen, branch, areas):
    """Converts internal to external bus numbering.

    This function performs several different tasks, depending on the
    arguments passed.

    1.  [BUS, GEN, BRANCH, AREAS] = INT2EXT(I2E, BUS, GEN, BRANCH, AREAS)
        [BUS, GEN, BRANCH] = INT2EXT(I2E, BUS, GEN, BRANCH)

    Converts from the consecutive internal bus numbers back to the originals
    using the mapping provided by the I2E vector returned from EXT2INT,
    where EXTERNAL_BUS_NUMBER = I2E(INTERNAL_BUS_NUMBER).

    Examples:
        [bus, gen, branch, areas] = int2ext(i2e, bus, gen, branch, areas)
        [bus, gen, branch] = int2ext(i2e, bus, gen, branch)

    2.  MPC = INT2EXT(MPC)

    If the input is a single MATPOWER case struct, then it restores all
    buses, generators and branches that were removed because of being
    isolated or off-line, and reverts to the original generator ordering
    and original bus numbering. This requires that the 'order' field
    created by EXT2INT be in place.

    Example:
        mpc = int2ext(mpc)

    3.  VAL = INT2EXT(MPC, VAL, OLDVAL, ORDERING)
        VAL = INT2EXT(MPC, VAL, OLDVAL, ORDERING, DIM)
        MPC = INT2EXT(MPC, FIELD, ORDERING)
        MPC = INT2EXT(MPC, FIELD, ORDERING, DIM)

    For a case struct using internal indexing, this function can be
    used to convert other data structures as well by passing in 2 to 4
    extra parameters in addition to the case struct. If the values passed
    in the 2nd argument (VAL) is a column vector, it will be converted
    according to the ordering specified by the 4th argument (ORDERING,
    described below). If VAL is an n-dimensional matrix, then the
    optional 5th argument (DIM, default = 1) can be used to specify
    which dimension to reorder. The 3rd argument (OLDVAL) is used to
    initialize the return value before converting VAL to external
    indexing. In particular, any data corresponding to off-line gens
    or branches or isolated buses or any connected gens or branches
    will be taken from OLDVAL, with VAL supplying the rest of the
    returned data.

    If the 2nd argument is a string or cell array of strings, it
    specifies a field in the case struct whose value should be
    converted as described above. In this case, the corresponding
    OLDVAL is taken from where it was stored by EXT2INT in
    MPC["order"].EXT and the updated case struct is returned.
    If FIELD is a cell array of strings, they specify nested fields.

    The ORDERING argument is used to indicate whether the data
    corresponds to bus-, gen- or branch-ordered data. It can be one
    of the following three strings: 'bus', 'gen' or 'branch'. For
    data structures with multiple blocks of data, ordered by bus,
    gen or branch, they can be converted with a single call by
    specifying ORDERING as a cell array of strings.

    Any extra elements, rows, columns, etc. beyond those indicated
    in ORDERING, are not disturbed.

    @see: ext2int
    @see: U{http://www.pserc.cornell.edu/matpower/}
    """
    if isinstance(i2e, dict):
        mpc = i2e
        if bus is None:#nargin == 1
            if not mpc.has_key('order'):
                logger.error('int2ext: mpc does not have the "order" field '
                    'require for conversion back to external numbering.')
            o = mpc["order"]

            if o["state"] == 'i':
                ## execute userfcn callbacks for 'int2ext' stage
                if mpc.has_key('userfcn'):
                    mpc = run_userfcn(mpc["userfcn"], 'int2ext', mpc)

                ## save data matrices with internal ordering & restore originals
                o["int"]["bus"]    = mpc["bus"]
                o["int"]["branch"] = mpc["branch"]
                o["int"]["gen"]    = mpc["gen"]
                mpc["bus"]     = o["ext"]["bus"]
                mpc["branch"]  = o["ext"]["branch"]
                mpc["gen"]     = o["ext"]["gen"]
                if mpc.has_key('gencost'):
                    o["int"]["gencost"] = mpc["gencost"]
                    mpc["gencost"] = o["ext"]["gencost"]
                if mpc.has_key('areas'):
                    o["int"]["areas"] = mpc["areas"]
                    mpc["areas"] = o["ext"]["areas"]
                if mpc.has_key('A'):
                    o["int"]["A"] = mpc["A"]
                    mpc["A"] = o["ext"]["A"]
                if mpc.has_key('N'):
                    o["int"]["N"] = mpc["N"]
                    mpc["N"] = o["ext"]["N"]

                ## update data (in bus, branch and gen only)
                mpc["bus"][o["bus"]["status"]["on"], :] = \
                    o["int"]["bus"]
                mpc["branch"][o["branch"]["status"]["on"], :] = \
                    o["int"]["branch"]
                mpc["gen"][o["gen"]["status"]["on"], :] = \
                    o["int"]["gen"][o["gen"]["i2e"], :]
                if mpc.has_key('areas'):
                    mpc["areas"][o["areas"]["status"]["on"], :] = \
                        o["int"]["areas"]

                ## revert to original bus numbers
                mpc["bus"][o["bus"]["status"]["on"], BUS_I] = \
                    o["bus"]["i2e"] \
                        [ mpc["bus"][o["bus"]["status"]["on"], BUS_I] ]
                mpc["branch"][o["branch"]["status"]["on"], F_BUS] = \
                    o["bus"]["i2e"] \
                        [ mpc["branch"][o["branch"]["status"]["on"], F_BUS] ]
                mpc["branch"][o["branch"]["status"]["on"], T_BUS] = \
                    o["bus"]["i2e"] \
                        [ mpc["branch"][o["branch"]["status"]["on"], T_BUS] ]
                mpc["gen"][o["gen"]["status"]["on"], GEN_BUS] = \
                    o["bus"]["i2e"] \
                        [ mpc["gen"][o["gen"]["status"]["on"], GEN_BUS] ]
                if mpc.has_key('areas'):
                    mpc["areas"][o["areas"]["status"]["on"], PRICE_REF_BUS] = \
                        o["bus"]["i2e"][ mpc["areas"] \
                         [o["areas"]["status"]["on"], PRICE_REF_BUS] ]

                if o.has_key('ext'):
                    del o['ext']
                o["state"] = 'e'
                mpc["order"] = o
            else:
                logger.error('int2ext: mpc claims it is already using '
                             'external numbering.')

            bus = mpc
        else:                    ## convert extra data
            if isinstance(bus, str) or isinstance(bus, list):   ## field
                field = bus
                ordering = gen
                if branch is not None:
                    dim = branch
                else:
                    dim = 1
                if isinstance(field, str):
                    mpc["order"]["int"]["field"] = mpc["field"]
                    mpc["field"] = int2ext(mpc, mpc["field"],
                                    mpc["order"].ext["field"], ordering, dim)
                else:
                    for k in range(len(field)):
                        s[k].type = '.'
                        s[k].subs = field[k]
                    if not mpc["order"].has_key('int'):
                        mpc["order"]["int"] = array([])
                    mpc["order"]["int"] = \
                        subsasgn(mpc["order"]["int"], s, subsref(mpc, s))
                    mpc = subsasgn(mpc, s, int2ext(mpc, subsref(mpc, s),
                        subsref(mpc["order"].ext, s), ordering, dim))
                bus = mpc
            else:                            ## value
                val = bus
                oldval = gen
                ordering = branch
                o = mpc["order"]
                if areas is not None:
                    dim = areas
                else:
                    dim = 1
                if isinstance(ordering, str):         ## single set
                    if ordering == 'gen':
                        v = get_reorder(val, o["ordering"]["i2e"], dim)
                    else:
                        v = val
                    bus = set_reorder(oldval, v,
                                      o["ordering"]["status"]["on"], dim)
                else:                            ## multiple sets
                    be = 0  ## base, external indexing
                    bi = 0  ## base, internal indexing
                    for k in range(len(ordering)):
                        ne = o["ext"]["ordering"][k].shape[0]
                        ni = mpc["ordering"][k].shape[0]
                        v = get_reorder(val, bi + range(ni), dim)
                        oldv = get_reorder(oldval, be + range(ne), dim)
                        new_v[k] = int2ext(mpc, v, oldv, ordering[k], dim)
                        be = be + ne
                        bi = bi + ni
                    ni = size(val, dim)
                    if ni > bi:              ## the rest
                        v = get_reorder(val, bi + range(ni), dim)
                        new_v[len(new_v) + 1] = v
                    bus = [dim] + new_v[:]
    else:            ## old form
        bus[:, BUS_I]               = i2e[ bus[:, BUS_I]            ]
        gen[:, GEN_BUS]             = i2e[ gen[:, GEN_BUS]          ]
        branch[:, F_BUS]            = i2e[ branch[:, F_BUS]         ]
        branch[:, T_BUS]            = i2e[ branch[:, T_BUS]         ]
        if areas is not None and branch is not None and not areas.any():
            areas[:, PRICE_REF_BUS] = i2e[ areas[:, PRICE_REF_BUS]  ]

    return bus, gen, branch, areas
