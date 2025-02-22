# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from libtbx.program_template import ProgramTemplate

from mmtbx.validation import rama_z
from mmtbx.validation.ramalyze import ramalyze
from mmtbx.validation.ramalyze import res_type_labels

from libtbx.utils import Sorry, null_out
from libtbx import Auto
import os

# =============================================================================

class Program(ProgramTemplate):

  description = '''
mmtbx.rama_z: Tool to calculate Rama-Z score. Validation of Ramachandran plot.

Usage examples:
  mmtbx.rama_z model1.pdb
  '''

  datatypes = ['model', 'phil']

  master_phil_str = """\
  write_HSL_models = False
    .type = bool
  write_HSL_plot = False
    .type = bool
  write_HSL_general_only = True
    .type = bool
  write_whole_plot = False
    .type = bool
  write_whole_general_only = True
    .type = bool
"""
  # write everything:
  # write_HSL_models=True write_HSL_plot=True write_HSL_general_only=False write_whole_plot=True write_whole_general_only=False
  # write only general plots:
  # write_HSL_plot=True write_whole_plot=False
  #
  # ---------------------------------------------------------------------------
  def validate(self):
    print('Validating inputs', file=self.logger)
    self.data_manager.has_models(expected_n=1, exact_count=True, raise_sorry=True)
    m = self.data_manager.get_model()
    if m.get_hierarchy().models_size() != 1:
      raise Sorry("Multi-model files are not supported.")

  # ---------------------------------------------------------------------------

  def _write_plots_if_needed(self, model, label, type_of_plot='whole'):
    write_plot = getattr(self.params, "write_%s_plot" % type_of_plot)
    write_general_only = getattr(self.params, "write_%s_general_only" % type_of_plot)
    if write_plot:
      self.rama = ramalyze(model.get_hierarchy(), out=null_out())
      self.plots = self.rama.get_plots(
          show_labels=False,
          point_style='.',
          markersize=3,
          markeredgecolor="red",
          dpi=300,
          markerfacecolor="yellow")
      plots_to_write = range(6)
      if write_general_only:
        plots_to_write = [0]
      for i in plots_to_write:
        file_label = res_type_labels[i].replace("/", "_")
        fn = "%s.png" % self.get_default_output_filename(
            prefix='%s_%s_' % (self.inp_fn, label),
            suffix=file_label,
            serial=Auto)
        if os.path.isfile(fn) and not self.params.output.overwrite:
          raise Sorry("%s already exists and overwrite is set to False." % fn)
        print("Saving:", fn, file=self.logger)
        self.plots[i].save_image(fn, dpi=300)

  def run(self):
    model = self.data_manager.get_model()
    self.inp_fn = os.path.basename(self.data_manager.get_default_model_name())[:-4]
    self.rama_z = rama_z.rama_z(
        model = model,
        log = self.logger)

    self._write_plots_if_needed(model, label='whole', type_of_plot='whole')
    helix_sel, sheet_sel, loop_sel = self.rama_z.get_ss_selections()
    for sel, label in [(helix_sel, "helix"),
         (sheet_sel, "sheet"),
         (loop_sel, "loop")]:
      selected_model = model.select(sel)
      if self.params.write_HSL_models:
        pdb_str = selected_model.model_as_pdb()
        fn = "%s" % self.get_default_output_filename(
            prefix='%s_' % self.inp_fn,
            suffix=label,
            serial=Auto)
        print("Writing out partial model: %s" % fn, file=self.logger)
        self.data_manager.write_model_file(selected_model, filename=fn)
      self._write_plots_if_needed(selected_model, label, type_of_plot='HSL')
    result = self.get_results()
    if result is None:
      print("Calculation of z-score failed for some reason", file=self.logger)
    else:
      for k in ["whole", "helix", "sheet", "loop"]:
        rc = k[0].upper()
        v = result.get(rc, None)
        if v is None:
          print("z-score %-5s: None, residues: %d" % (k, result['residue_counts'][rc]), file=self.logger)
        else:
          print("z-score %-5s: %5.2f (%4.2f), residues: %d" % (k, v[0], v[1], result['residue_counts'][rc]), file=self.logger)

  # ---------------------------------------------------------------------------
  def get_results(self):
    r = self.rama_z.get_z_scores()
    r['residue_counts'] = self.rama_z.get_residue_counts()
    return r
