.. _level3-asn-rules:

Level3 Associations: Rules
==========================

.. _level3-asn-data-grouping:

Data Grouping
-------------

JWST exposures are identified and grouped in a specific order, as
follows:

- program

  The entirety of a science observing proposal is contained within a
  `program`. All observations, regardless of instruments, pertaining
  to a proposal are identified by the program id.
  
- observation

  A set of visits, any corresponding auxiliary
  exposures, such as wavelength calibration, using a specific
  instrument. An observation does not necessarily contain all the
  exposures required for a specific observation mode. Also, exposures
  within an observation can be taken with different optical
  configurations of the same instrument
  
- visit

  A set of exposures which sharing the same source, or target, whether that would
  be external to the observatory or internal to the instrument. The
  can be many visits for the same target, and visits to different
  targets can be interspersed among themselves.
  
- group

  A set of exposures that share the same observatory configuration.
  This is basically a synchronization point between observatory moves
  and parallel instrument observations.
  
- sequence

  *TBD*
  
- activity

  A set of exposures that are to be taken atomically. All exposures
  within an activity are associated with each other and have been
  taken consecutively. 

- exposure

  The basic unit of science data. Starting at Level1b, an exposure
  contains a single integrations of a single detector from a single
  instrument for a single *snap*. Note that a single integration
  actually is a number of readouts of the detector during the integration.
  
.. _level3-asn-association-types:

Association Types
-----------------

Each Level3 association is intended to make a specific science
product. The type of science product is indicated by the `ATYPE` field
in the association file name (see :ref:`asn-DMS-naming`), and in the `asn_type` meta
keyword of the association itself (see :ref:`asn-association-meta-keywords`).

The pipeline uses this type as the key to indicate which Level 3
pipeline module to use to process this association.

The current association types are:

  * `image`: suitable for CALIMAGE3 processing
  * `spec`: suitable for CALSPECE3 processing
  * `wfs`: Wave front sensing data, used by `wfs_combine`
  * `ami`: Aperture Mask Interferometry
  * `coron`: Coronography
  * `tso`: Time-series Observations
  * `wfss`: Wide-Field Slitless Spectroscopy
  * `nrsifu`: NIRSpec IFU Spectroscopy
    
    This is different from just spectroscopy because of how NIRSpec
    is arranged. The wavelength/dispersion is determined by the
    Prism/Grating wheel. The Filter wheel does not modified
    wavelength/dispersion, thus allowing exposures in multiple
    wavelengths to be combined.

.. _level3-asn-rule-definitions:

Rules
-----

All rules have as their base class :class:`DMS_Level3_Base
<jwst.associations.lib.rules_level3_base.DMS_Level3_Base>` This class
defines the association structure, enforces the DMS naming
conventions, and defines the basic validity checks on the Level3
associations.

Along with the base class, a number of mixin classes are defined.
These mixins define some basic constraints that are found in a number
of rules. An example is the :class:`AsnMixin_Base
<jwst.associations.lib.rules_level3_base.AsnMixin_Base>`, which
provides the constraints that ensure that the program identificaiton
and instrument are the same in each association.

The rules themselves are subclasses of :class:`AsnMixin_Base
<jwst.associations.lib.rules_level3_base.AsnMixin_Base>` and whatever
other mixin classes are necessary to build the rule. Conforming to the
:ref:`class-naming` scheme, all the final
Level3 association rules begin with `Asn_`. An example is the
:class:`Asn_Image <jwst.associations.lib.rules_level3.Asn_Image>` rule.

The following figure shows the above relationships. Note that this
diagram is not meant to be a complete listing.

.. figure:: ../graphics/level3_rule_inheritance.png
   :scale: 50%

   Level3 Rule Class Inheritance

Level3 Rules
------------

.. automodule:: jwst.associations.lib.rules_level3
   :members:
   :member-order: bysource
