# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from django.db import migrations, models
import datetime
import crds.server.interactive.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AuditBlob',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', help_text=b'unique name of this model.', max_length=64, blank=True)),
                ('blob', models.TextField(default=b'{}', help_text=b'repr() of value of this blob,  probably repr(dict).')),
                ('user', models.CharField(default=b'', help_text=b'user who performed this action', max_length=64)),
                ('date', models.CharField(default=b'', help_text=b'date of this action', max_length=26)),
                ('action', models.CharField(default=b'', help_text=b'name of action performed', max_length=64, choices=[(b'mass import', b'mass import'), (b'submit file', b'submit file'), (b'blacklist', b'blacklist'), (b'new context', b'new context'), (b'batch submit', b'batch submit'), (b'set default context', b'set default context'), (b'delete references', b'delete references'), (b'add references', b'add references'), (b'add_files tool', b'add_files tool')])),
                ('filename', models.CharField(default=b'', help_text=b'unique name of this model.', max_length=64)),
                ('observatory', models.CharField(default=b'jwst', help_text=b'observatory this action applied to.', max_length=8)),
                ('instrument', models.CharField(default=b'', help_text=b'instrument this action applied to.', max_length=32, blank=True)),
                ('filekind', models.CharField(default=b'', help_text=b'filekind this action applied to.', max_length=32, blank=True)),
                ('why', models.TextField(default=b'', help_text=b'reason this action was performed', blank=True)),
                ('details', models.TextField(default=b'', help_text=b'supplementary info', blank=True)),
            ],
            options={
                'db_table': 'crds_jwst_actions',
            },
        ),
        migrations.CreateModel(
            name='ContextHistoryModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', help_text=b'unique name of this model.', max_length=64, blank=True)),
                ('start_date', models.DateTimeField()),
                ('context', models.CharField(default=b'', help_text=b'name of .pmap assigned to for this kind of context.', max_length=64)),
                ('state', models.CharField(default=b'operational', max_length=32, choices=[(b'operational', b'operational'), (b'edit', b'edit'), (b'versions', b'versions')])),
                ('description', models.TextField(default=b'routine update', help_text=b'Reason for the switch to this context.')),
            ],
            options={
                'ordering': ('start_date', 'context'),
                'db_table': 'crds_jwst_context_history',
            },
        ),
        migrations.CreateModel(
            name='ContextModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', help_text=b'unique name of this model.', max_length=64, blank=True)),
                ('context', models.CharField(default=b'', help_text=b'name of .pmap assigned to for this kind of context.', max_length=64)),
            ],
            options={
                'db_table': 'crds_jwst_contexts',
            },
        ),
        migrations.CreateModel(
            name='CounterModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', help_text=b'unique name of this model.', max_length=64, blank=True)),
                ('counter', models.IntegerField(default=0, help_text=b'Value of the counter.')),
            ],
            options={
                'db_table': 'crds_jwst_counters',
            },
        ),
        migrations.CreateModel(
            name='FileBlob',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', help_text=b'unique name of this model.', max_length=64, blank=True)),
                ('blob', models.TextField(default=b'{}', help_text=b'repr() of value of this blob,  probably repr(dict).')),
                ('state', models.CharField(default=b'delivered', help_text=b'operational status of this file.', max_length=32, choices=[(b'delivered', b'delivered'), (b'submitted', b'submitted'), (b'archiving', b'archiving'), (b'archived', b'archived'), (b'operational', b'operational'), (b'uploaded', b'uploaded'), (b'cancelled', b'cancelled'), (b'archiving-failed', b'archiving-failed')])),
                ('blacklisted', models.BooleanField(default=False, help_text=b'If True, this file should not be used, transitive to referencers.')),
                ('rejected', models.BooleanField(default=False, help_text=b'If True, this file should not be used, non-transitive.')),
                ('observatory', models.CharField(default=b'jwst', help_text=b'observatory associated with file', max_length=8, choices=[(b'hst', b'hst'), (b'jwst', b'jwst')])),
                ('instrument', models.CharField(default=b'', help_text=b'instrument associated with file', max_length=16, choices=[(b'fgs', b'fgs'), (b'miri', b'miri'), (b'nircam', b'nircam'), (b'niriss', b'niriss'), (b'nirspec', b'nirspec'), (b'system', b'system'), (b'unknown', b'unknown')])),
                ('filekind', models.CharField(default=b'', help_text=b'dataset keyword associated with this file', max_length=32, choices=[(b'amplifier', b'amplifier'), (b'area', b'area'), (b'badshutter', b'badshutter'), (b'calver', b'calver'), (b'camera', b'camera'), (b'collimator', b'collimator'), (b'cubepar', b'cubepar'), (b'dark', b'dark'), (b'datalvl', b'datalvl'), (b'dflat', b'dflat'), (b'disperser', b'disperser'), (b'distortion', b'distortion'), (b'drizpars', b'drizpars'), (b'extract1d', b'extract1d'), (b'fflat', b'fflat'), (b'filteroffset', b'filteroffset'), (b'flat', b'flat'), (b'fore', b'fore'), (b'fpa', b'fpa'), (b'fringe', b'fringe'), (b'gain', b'gain'), (b'ifufore', b'ifufore'), (b'ifupost', b'ifupost'), (b'ifuslicer', b'ifuslicer'), (b'ipc', b'ipc'), (b'lastframe', b'lastframe'), (b'linearity', b'linearity'), (b'mask', b'mask'), (b'msa', b'msa'), (b'msaoper', b'msaoper'), (b'ote', b'ote'), (b'pathloss', b'pathloss'), (b'photom', b'photom'), (b'readnoise', b'readnoise'), (b'refpix', b'refpix'), (b'regions', b'regions'), (b'reset', b'reset'), (b'resol', b'resol'), (b'rscd', b'rscd'), (b'saturation', b'saturation'), (b'sflat', b'sflat'), (b'specwcs', b'specwcs'), (b'straymask', b'straymask'), (b'superbias', b'superbias'), (b'throughput', b'throughput'), (b'v2v3', b'v2v3'), (b'wavelengthrange', b'wavelengthrange'), (b'wcsregions', b'wcsregions'), (b'unknown', b'unknown')])),
                ('type', models.CharField(default=b'', help_text=b'type of file,  reference data or CRDS rule or context', max_length=32, choices=[(b'reference', b'reference'), (b'mapping', b'mapping')])),
                ('derived_from', models.CharField(default=b'none', help_text=b'Previous version of this file this one was based on.', max_length=128)),
                ('sha1sum', models.CharField(default=b'none', help_text=b'Hex sha1sum of file contents as delivered', max_length=40)),
                ('delivery_date', models.DateTimeField(default=datetime.datetime.now, help_text=b'Date file was received by CRDS.')),
                ('activation_date', models.DateTimeField(default=datetime.datetime(2050, 1, 1, 0, 0), help_text=b'Date file first listed in an operational context.')),
                ('useafter_date', models.DateTimeField(default=datetime.datetime(1900, 1, 1, 0, 0), help_text=b'Dataset date after which this file is a valid reference.')),
                ('change_level', models.CharField(default=b'SEVERE', help_text=b'Affect of changes in this file relative to preceding version on science results', max_length=16, choices=[(b'SEVERE', b'SEVERE'), (b'MODERATE', b'MODERATE'), (b'TRIVIAL', b'TRIVIAL')])),
                ('pedigree', models.CharField(default=b'', help_text=b'From PEDIGREE, reference characterization, e.g. GROUND 16/07/2008 16/07/2010', max_length=80, blank=True)),
                ('reference_file_type', models.CharField(default=b'', help_text=b'From REFTYPE,  description of file type.', max_length=80, blank=True)),
                ('size', models.BigIntegerField(default=-1, help_text=b'size of file in bytes.')),
                ('uploaded_as', models.CharField(default=b'', help_text=b'original upload filename', max_length=80, blank=True)),
                ('creator_name', models.CharField(default=b'', help_text=b'person who made this file,  possibly/likely not the submitter', max_length=80, blank=True)),
                ('deliverer_user', models.CharField(default=b'', help_text=b'username who uploaded the file', max_length=80, blank=True)),
                ('deliverer_email', models.CharField(default=b'', help_text=b"person's e-mail who uploaded the file", max_length=80, blank=True)),
                ('description', models.TextField(default=b'none', help_text=b'Brief rationale for changes to this file.', blank=True)),
                ('catalog_link', models.CharField(default=b'', help_text=b'', max_length=128, blank=True)),
                ('replaced_by_filename', models.CharField(default=b'', help_text=b'', max_length=128, blank=True)),
                ('comment', models.TextField(default=b'none', help_text=b'from DESCRIP keyword of reference file.', blank=True)),
                ('aperture', models.CharField(default=b'none', help_text=b'from APERTURE keyword of reference file.', max_length=80, blank=True)),
                ('history', models.TextField(default=b'none', help_text=b'History extracted from reference file.', blank=True)),
            ],
            options={
                'db_table': 'crds_jwst_catalog',
            },
            bases=(models.Model, crds.server.interactive.models.FileBlobRepairMixin),
        ),
        migrations.CreateModel(
            name='RemoteContextModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', help_text=b'unique name of this model.', max_length=64, blank=True)),
                ('observatory', models.CharField(default=b'none', help_text=b'Observatory this context applies to.', max_length=32)),
                ('kind', models.CharField(default=b'none', help_text=b'operational, edit, etc.', max_length=64)),
                ('key', models.CharField(default=b'none', help_text=b'Observatory this context applies to.', max_length=128)),
                ('context', models.CharField(default=b'none', help_text=b'Name of context in use by remote cache.', max_length=64)),
            ],
            options={
                'db_table': 'crds_jwst_remote_context',
            },
        ),
        migrations.CreateModel(
            name='RepeatableResultBlob',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default=b'', help_text=b'unique name of this model.', max_length=64, blank=True)),
                ('blob', models.TextField(default=b'{}', help_text=b'repr() of value of this blob,  probably repr(dict).')),
            ],
            options={
                'db_table': 'crds_jwst_results',
            },
        ),
    ]
