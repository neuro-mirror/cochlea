# Author: Marek Rudnicki
# Time-stamp: <2010-04-02 15:19:37 marek>
#
# Description: Sumner et al. ``A nonlinear filter-bank model of the
# guinea-pig cochlear nerve: Rate responses''
# J. Acoust. Soc. Am. Volume 113, Issue 6, pp. 3264-3274 (June 2003)

from __future__ import division

import numpy as np

import thorns as th
import dsam

from auditory_periphery import AuditoryPeriphery, par_dir

class Sumner2003(AuditoryPeriphery):
    def __init__(self, anf_num=(1,1,1), cf=1000,
                 sg_type='carney', accumulate=False):
        """ Auditory periphery model from Sumner (2003)

        anf_num: (hsr_num, msr_num, lsr_num)
        cf: CF
        sg_type: 'carney', 'binomial'
        accumulate: if True, spikes for all fibers are calculated at once

        """
        self.name = 'Sumner2003'

        self._accumulate = accumulate

        self._hsr_num = anf_num[0]
        self._msr_num = anf_num[1]
        self._lsr_num = anf_num[2]


        # TODO: check the filters
        self.middle_ear_module_A = dsam.EarModule("Filt_MultiBPass")
        self.middle_ear_module_A.read_pars(par_dir("filt_GPa_Sumner2003.par"))

        self.middle_ear_module_B = dsam.EarModule("Filt_MultiBPass")
        self.middle_ear_module_B.read_pars(par_dir("filt_GPb_Sumner2003.par"))
        dsam.connect(self.middle_ear_module_A, self.middle_ear_module_B)


        # Stapes velocity [Pa -> m/s]
        self.stapes_module = dsam.EarModule("Util_mathOp")
        self.stapes_module.read_pars(par_dir("stapes_Sumner2003.par"))
        dsam.connect(self.middle_ear_module_B, self.stapes_module)


        # Basilar membrane
        self.bm_module = dsam.EarModule("BM_DRNL")
        self.bm_module.read_pars(par_dir("bm_Sumner2003.par"))
        self.set_freq(cf)
        dsam.connect(self.stapes_module, self.bm_module)


        # IHC receptor potential
        self.ihcrp_module = dsam.EarModule("IHCRP_Shamma3StateVelIn")
        self.ihcrp_module.read_pars(par_dir("ihcrp_Sumner2002.par"))
        dsam.connect(self.bm_module, self.ihcrp_module)


        if self._hsr_num > 0:
            self.ihc_hsr_module = dsam.EarModule("IHC_Meddis2000")
            self.ihc_hsr_module.read_pars(par_dir("ihc_hsr_Sumner2003.par"))
            dsam.connect(self.ihcrp_module, self.ihc_hsr_module)

            self.sg_hsr_module = self._generate_anf(self._hsr_num,
                                              sg_type,
                                              accumulate)
            dsam.connect(self.ihc_hsr_module, self.sg_hsr_module)

        if self._msr_num > 0:
            self.ihc_msr_module = dsam.EarModule("IHC_Meddis2000")
            self.ihc_msr_module.read_pars(par_dir("ihc_msr_Sumner2003.par"))
            dsam.connect(self.ihcrp_module, self.ihc_msr_module)

            self.sg_msr_module = self._generate_anf(self._msr_num,
                                              sg_type,
                                              accumulate)
            dsam.connect(self.ihc_msr_module, self.sg_msr_module)

        if self._lsr_num > 0:
            self.ihc_lsr_module = dsam.EarModule("IHC_Meddis2000")
            self.ihc_lsr_module.read_pars(par_dir("ihc_lsr_Sumner2003.par"))
            dsam.connect(self.ihcrp_module, self.ihc_lsr_module)

            self.sg_lsr_module = self._generate_anf(self._lsr_num,
                                              sg_type,
                                              accumulate)
            dsam.connect(self.ihc_lsr_module, self.sg_lsr_module)



    def set_freq(self, cf):
        # Test for `cf' type, should be either float or tuple
        # flaot: single BM frequency
        # tuple: (min_freq, max_freq, freq_num)
        if isinstance(cf, int):
            cf = float(cf)
        assert (isinstance(cf, tuple) or
                isinstance(cf, float))

        if isinstance(cf, float):
            self.bm_module.set_par("CF_MODE", "single")
            self.bm_module.set_par("SINGLE_CF", cf)
        elif isinstance(cf, tuple):
            self.bm_module.set_par("CF_MODE", "guinea_pig")
            self.bm_module.set_par("MIN_CF", cf[0])
            self.bm_module.set_par("MAX_CF", cf[1])
            self.bm_module.set_par("CHANNELS", cf[2])


    def get_freq_map(self):
        """ Returns the current frequancy map.

        Note: since frequency map is created during simulation, this
        function hast to be called after run()

        """
        return self.bm_module.get_labels()


    def print_pars(self):
        self.bm_module.print_pars()
        if self._hsr_num > 0:
            self.ihc_hsr_module.print_pars()

        if self._msr_num > 0:
            self.ihc_msr_module.print_pars()

        if self._lsr_num > 0:
            self.ihc_lsr_module.print_pars()


    def run(self, fs, sound):
        """ Run auditory periphery model.

        fs: sampling frequency
        sound: audio signal

        """
        self.middle_ear_module_A.run(fs, sound)
        self.middle_ear_module_B.run()

        self.stapes_module.run()
        self.bm_module.run()
        self.ihcrp_module.run()

        import biggles
        trains = []
        if self._hsr_num > 0:
            biggles.plot(self.ihcrp_module.get_signal())
            self.ihc_hsr_module.run()
            biggles.plot(self.ihc_hsr_module.get_signal())
            tr = self._run_anf('hsr', self.sg_hsr_module,
                               fs, self._hsr_num, self._accumulate)
            trains.extend(tr)

        if self._msr_num > 0:
            self.ihc_msr_module.run()
            tr = self._run_anf('msr', self.sg_msr_module,
                               fs, self._msr_num, self._accumulate)
            trains.extend(tr)

        if self._lsr_num > 0:
            self.ihc_lsr_module.run()
            tr = self._run_anf('lsr', self.sg_lsr_module,
                               fs, self._lsr_num, self._accumulate)
            trains.extend(tr)

        trains = np.array(trains, dtype=self._train_type)

        return trains



def main():
    fs = 100000
    cf = 1000
    stimdb = 70

    ear = Sumner2003((250,0,0), cf=cf)

    t = np.arange(0, 0.1, 1/fs)
    s = np.sin(2 * np.pi * t * cf)
    s = dsam.set_dbspl(stimdb, s)
    z = np.zeros(np.ceil(len(t)/3))
    s = np.concatenate( (z, s, z) )

    anf = ear.run(fs, s)

    p = th.plot_raster(anf['spikes'])
    p.show()

    p = th.plot_psth(anf['spikes'])
    p.show()


if __name__ == "__main__":
    main()

