"""Transport physics of a monolayer-graphene Hall bar on SiO2.

This module is pure: it holds no instrument state and no time. Given a
gate voltage, a field, a temperature and a bias it returns what the sample
does. Everything that makes a *measurement* of it imperfect — lock-in lag,
noise, ramping, self-heating history — lives in :mod:`unisweep.sim.rig`.

The model, and where each piece comes from
------------------------------------------

**Carrier density.** The back gate is a parallel-plate capacitor, so the
gate-induced density is ``n_cv = C_ox (Vg - V_D) / e``. At the Dirac point
the density does not reach zero: disorder breaks the sheet into
electron/hole puddles, and thermal excitation adds carriers of both signs.
Both are folded into a residual density ``n_0`` and the two carrier
populations follow the mass-action form

    n = ½[ n_cv + sqrt(n_cv² + 4 n_0²) ]      p = ½[ -n_cv + sqrt(...) ]

so that ``n - p = n_cv`` and ``n·p = n_0²`` (Dorgan et al., APL 97, 082112
(2010), Eq. 3). Measured ``n_0`` on SiO2 is 1.9-5.4e11 cm^-2 by quantum
capacitance (Appl. Phys. Lett. 102, 173507 (2013)).

**Scattering.** Graphene's linear dispersion makes the resistivity from
isotropic scatterers independent of carrier density, which is why the
phonon terms below are added to the *resistivity* and not to a mobility.
Chen et al., Nature Nanotech. 3, 206 (2008) measured this directly:

* charged impurities give a roughly density-independent mobility
  ``mu_imp`` (sigma proportional to n);
* acoustic phonons contribute ``rho_A = a·T`` with ``a ≈ 0.1 ohm/K``,
  reaching only 30 ohm at room temperature — the intrinsic limit, and a
  mobility ceiling of 2e5 cm²/Vs;
* surface polar phonons of the SiO2 substrate switch on above ~200 K as
  ``rho_SPP = b / (exp(E0/kT) - 1)`` with ``E0 ≈ 59 meV``, and are what
  actually limits room-temperature mobility on SiO2 to ~4e4 cm²/Vs.

``b`` here is calibrated so that the two phonon terms together reproduce
that 4e4 cm²/Vs ceiling at n = 1e12 cm^-2 and T = 300 K; see
:func:`_default_spp_prefactor`.

**Magnetotransport.** Two carrier species in a Drude conductivity tensor.
This is not a convenience — it is what makes the Dirac region behave: a
single-carrier model gives a magnetoresistance that is exactly flat and a
Hall slope that never turns over, whereas real graphene near charge
neutrality shows strong positive magnetoresistance and a non-linear,
sign-changing Hall response. Both come out of the two-carrier tensor for
free.

**Quantum regime.** Landau quantisation is blended in with a weight
``w = R_T · R_D`` built from the standard Lifshitz-Kosevich thermal factor
and the Dingle factor, so the same damping that sets the Shubnikov-de Haas
amplitude also sets how well the Hall plateaus are formed. The cyclotron
mass is the Dirac one, ``m_c = ħ sqrt(π n) / v_F``.

The oscillation is periodic in 1/B with frequency ``B_F = n h / 4e`` (the
4 is spin and valley degeneracy), and — this is the part specific to
graphene — the minima sit at *half-integer* ``B_F/B``, giving the
half-integer quantum Hall sequence ``nu = ±2, ±6, ±10, ...``. That phase
offset is the Berry phase of π, and it is exactly what a fan diagram or a
fit to the SdH phase is supposed to recover.

**What is deliberately not modelled.** Electron-electron interaction
effects, the ν = 0 and ν = ±1 broken-symmetry states at high field,
fractional filling, ballistic/hydrodynamic transport, and quantum
capacitance corrections to the gate. None of them are needed for the
measurements this rig is meant to teach, and each would add parameters
that cannot be pinned by the published numbers above.

Sources
-------
* J.-H. Chen, C. Jang, S. Xiao, M. Ishigami, M. S. Fuhrer, "Intrinsic and
  extrinsic performance limits of graphene devices on SiO2", Nature
  Nanotechnology 3, 206-209 (2008); arXiv:0711.3646.
* V. E. Dorgan, M.-H. Bae, E. Pop, "Mobility and saturation velocity in
  graphene on SiO2", Appl. Phys. Lett. 97, 082112 (2010).
* J. Xia et al. / quantum-capacitance residual density, Appl. Phys. Lett.
  102, 173507 (2013); arXiv:1304.3957.
* A. Konar, T. Fang, D. Jena, surface polar phonon transport in graphene,
  arXiv:1010.4772 (SiO2 SPP mode at 60.0 meV).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

__all__ = ["GrapheneSample", "PHYS"]


# --- physical constants (CODATA 2018) --------------------------------------
E_CHARGE = 1.602176634e-19        # C
H_PLANCK = 6.62607015e-34         # J s
HBAR = 1.054571817e-34            # J s
K_B = 1.380649e-23                # J/K
EPS0 = 8.8541878128e-12           # F/m
V_FERMI = 1.0e6                   # m/s, graphene Fermi velocity
R_K = H_PLANCK / E_CHARGE ** 2    # 25812.807... ohm, von Klitzing

PHYS = {"e": E_CHARGE, "h": H_PLANCK, "hbar": HBAR, "kB": K_B,
        "eps0": EPS0, "vF": V_FERMI, "R_K": R_K}

_CM2 = 1e4        # m^-2 per cm^-2
_CM2_PER_VS = 1e-4    # m²/Vs per cm²/Vs


def _default_spp_prefactor(acoustic_per_K: float = 0.10,
                           spp_energy_meV: float = 59.0,
                           rt_mobility_cm2Vs: float = 4.0e4,
                           at_density_cm2: float = 1.0e12) -> float:
    """The surface-polar-phonon prefactor, in ohms.

    Chen et al. quote two numbers we can anchor to: acoustic phonons alone
    give 30 ohm at 300 K, and the SiO2 substrate limits room-temperature
    mobility to ~4e4 cm²/Vs at technologically relevant density. Those two
    fix the SPP term with no free parameter left over.
    """
    n = at_density_cm2 * _CM2
    mu = rt_mobility_cm2Vs * _CM2_PER_VS
    rho_phonon_300 = 1.0 / (n * E_CHARGE * mu)      # ~156 ohm/sq
    rho_acoustic_300 = acoustic_per_K * 300.0       # 30 ohm/sq
    rho_spp_300 = max(rho_phonon_300 - rho_acoustic_300, 1.0)
    kT_300 = K_B * 300.0 / E_CHARGE * 1e3           # meV
    return rho_spp_300 * (math.exp(spp_energy_meV / kT_300) - 1.0)


@dataclass
class GrapheneSample:
    """A specific piece of graphene, with its own disorder and geometry.

    Every field is something a real device would differ in. The values
    here describe an ordinary exfoliated monolayer on 300 nm SiO2 — good
    enough to see the quantum Hall effect at a few tesla and a few kelvin,
    not a record-breaking hBN-encapsulated device.

    Densities are in cm^-2 and mobilities in cm²/Vs, because that is how
    they are quoted in the literature and on whiteboards; everything is
    converted to SI on the way in.
    """

    # --- identity ---------------------------------------------------------
    sample_id: str = "SIM-GR-01"
    description: str = ("monolayer graphene on 300 nm SiO2/Si, "
                        "exfoliated, Hall bar")

    # --- geometry ---------------------------------------------------------
    width_um: float = 2.0
    """Channel width between the Hall probe pair."""
    length_um: float = 6.0
    """Separation of the longitudinal (Vxx) voltage probes."""

    # --- gate -------------------------------------------------------------
    dielectric: str = "SiO2"
    """Label only; the numbers below are what matter. 'SiO2' and 'hBN' are
    the two this lab uses, and they behave very differently: 300 nm of
    thermal oxide gives 7.2e10 cm^-2 per volt and tolerates tens of volts,
    while 30 nm of hBN gives ten times the capacitance and leaks by 10 V.
    Which one a given device has is something the operator states when the
    work is assigned; nothing here can know it."""
    oxide_thickness_nm: float = 300.0
    oxide_epsilon: float = 3.9
    dirac_voltage: float = 8.5
    """Gate voltage of the charge-neutrality point. Positive means the
    sheet is p-doped at zero gate — the usual state of graphene on SiO2
    after exposure to air."""

    # --- top gate (0 thickness = no top gate) ------------------------------
    top_gate_thickness_nm: float = 0.0
    """Set non-zero for a dual-gated device. With a top gate the density
    and the displacement field become independent knobs, which is what the
    'repeat at different D' step needs."""
    top_gate_epsilon: float = 3.4
    top_gate_offset_V: float = 0.0

    # --- electron cooling -------------------------------------------------
    cooling_exponent: float = 3.0
    """Delta in the cooling law ``P/A = Sigma (Te^delta - T_lattice^delta)``.
    3 is disorder-assisted supercollision cooling, which is what graphene on
    an imperfect substrate does; 4 is the clean acoustic-phonon result.
    Telling those two apart from a Te-versus-absorbed-power series is the
    point of the exercise, so this is the hidden answer, not a setting."""
    cooling_coefficient: float = 5.0
    """Sigma at the reference density, W m^-2 K^-delta. The supercollision
    coupling scales linearly with carrier density (A ~ nu^2(E_F) ~ n), so it
    is quoted here at one density and scaled from there.

    Set so that a 100 nA excitation at 4 K lifts the electrons by under a
    tenth of a kelvin while a microamp lifts them by several — which is the
    regime real devices are in, and the reason people measure with
    nanoamps. Published supercollision coefficients span about an order of
    magnitude between devices, so treat this as a per-device number."""
    cooling_reference_density_cm2: float = 1.0e12

    thz_absorptance: float = 0.023
    """Fraction of the power reaching the sheet that is absorbed. 2.3% is
    pi*alpha, the universal interband value; at sub-THz the Drude term
    dominates and an antenna or a resonator can raise this by orders of
    magnitude, so treat it as a per-device number."""
    drude_scattering_time_s: float = 4.0e-14
    """Sets where Drude absorption rolls off with frequency."""

    # --- disorder ---------------------------------------------------------
    puddle_density_cm2: float = 1.8e11
    """Residual carrier density at the Dirac point from electron-hole
    puddles. 1.9-5.4e11 cm^-2 measured on SiO2 by quantum capacitance."""
    mobility_impurity_cm2Vs: float = 14000.0
    """Charged-impurity-limited mobility: temperature-independent, and in
    graphene roughly density-independent."""
    rho_short_ohm: float = 45.0
    """Short-range (point-defect) scattering: a density-independent
    resistivity floor."""

    # --- phonons ----------------------------------------------------------
    rho_acoustic_per_K: float = 0.10
    """Acoustic-phonon resistivity slope, ohm/K. 0.1 gives Chen's 30 ohm
    at room temperature."""
    spp_energy_meV: float = 59.0
    """SiO2 surface polar phonon energy. Reported as 59-60 meV."""
    spp_prefactor_ohm: float = field(default_factory=_default_spp_prefactor)

    # --- quantum ----------------------------------------------------------
    dingle_temperature_K: float = 8.0
    """Sets the field at which Landau levels resolve. Lower = cleaner.
    8 K puts the onset of Shubnikov-de Haas oscillations near 2 T and a
    well-formed nu = 2 plateau within a 9 T magnet."""
    quantum_enabled: bool = True

    # --- weak localisation (off by default; see module docstring) ---------
    weak_localisation: float = 0.0
    """Amplitude of a low-field weak-localisation dip, in units of e²/πh.
    Realistic for graphene on SiO2 below ~20 K, but it puts a sharp
    even-in-B feature at B = 0 that complicates a first Hall extraction,
    so it is off unless a scenario asks for it."""
    wl_field_T: float = 0.02
    """Phase-coherence field scale of that dip."""

    # --- contacts and probes ----------------------------------------------
    contact_resistance_ohm: float = 420.0
    """Per-contact series resistance. Cancels in a 4-probe lock-in
    measurement and does not cancel in a 2-probe DC one — which is how a
    reader is supposed to tell them apart."""
    hall_misalignment: float = 0.025
    """Fraction of Rxx that leaks into the measured Rxy because the Hall
    probes are not exactly opposite one another. Even in B, so symmetrising
    the field removes it exactly. This is the single most common reason a
    Hall density comes out wrong."""

    # --- thermal ----------------------------------------------------------
    thermal_resistance_K_per_W: float = 1.0e4
    """Sample-to-bath thermal resistance; ~1e4 K/W for graphene on 300 nm
    SiO2 (Dorgan et al.). Turns bias into electron temperature."""

    # --- gate oxide integrity ---------------------------------------------
    leakage_scale_A: float = 1.0e-12
    leakage_voltage_V: float = 8.0
    """Leakage grows as exp(|Vg|/leakage_voltage_V); with the defaults it
    passes 1 nA near 55 V and 10 nA near 75 V."""
    breakdown_voltage_V: float = 85.0
    """Beyond this the oxide is destroyed. The rig latches it."""

    # ==================================================================
    # derived quantities
    # ==================================================================
    @property
    def oxide_capacitance(self) -> float:
        """Gate capacitance per unit area, F/m². 1.15e-4 for 300 nm SiO2,
        i.e. 7.2e10 cm^-2 per volt."""
        return EPS0 * self.oxide_epsilon / (self.oxide_thickness_nm * 1e-9)

    @property
    def density_per_volt_cm2(self) -> float:
        """Carriers added per volt of gate, cm^-2 V^-1."""
        return self.oxide_capacitance / E_CHARGE / _CM2

    @property
    def top_gate_capacitance(self) -> float:
        """Top-gate capacitance per unit area, F/m². Zero if there is no
        top gate."""
        if self.top_gate_thickness_nm <= 0.0:
            return 0.0
        return EPS0 * self.top_gate_epsilon / (self.top_gate_thickness_nm
                                               * 1e-9)

    @property
    def has_top_gate(self) -> bool:
        return self.top_gate_thickness_nm > 0.0

    @property
    def aspect_ratio(self) -> float:
        """Number of squares between the longitudinal voltage probes."""
        return self.length_um / self.width_um

    @property
    def channel_area_m2(self) -> float:
        """Area the dissipated power is spread over."""
        return (self.width_um * 1e-6) * (self.length_um * 1e-6)

    def displacement_field(self, gate_v: float, top_gate_v: float = 0.0,
                           dirac_v: float | None = None) -> float:
        """Out-of-plane displacement field D/eps0, in V/nm.

        Zero without a top gate: a single gate cannot separate density from
        field, which is exactly why the D-dependence step needs one.
        """
        if not self.has_top_gate:
            return 0.0
        v_d = self.dirac_voltage if dirac_v is None else dirac_v
        bottom = self.oxide_capacitance * (gate_v - v_d)
        top = self.top_gate_capacitance * (top_gate_v
                                           - self.top_gate_offset_V)
        return 0.5 * (bottom - top) / EPS0 * 1e-9

    def thermal_density(self, T: float) -> float:
        """Thermally excited carriers of each sign, m^-2.

        ``n_th = (pi/6)(kT / hbar v_F)²`` — about 8e10 cm^-2 at 300 K, so
        comparable to the puddle density and not negligible at room
        temperature.
        """
        if T <= 0.0:
            return 0.0
        return (math.pi / 6.0) * (K_B * T / (HBAR * V_FERMI)) ** 2

    def residual_density(self, T: float) -> float:
        """Puddles and thermal carriers combined, m^-2."""
        n_puddle = self.puddle_density_cm2 * _CM2
        n_th = self.thermal_density(T)
        return math.hypot(n_puddle, n_th)

    def gate_density(self, gate_v: float, dirac_v: float | None = None,
                     top_gate_v: float = 0.0) -> float:
        """Signed gate-induced density, m^-2. Positive means electrons.

        Both gates add carriers; only their difference makes a displacement
        field. With no top gate the second term is identically zero.
        """
        v_d = self.dirac_voltage if dirac_v is None else dirac_v
        bottom = self.oxide_capacitance * (gate_v - v_d)
        top = self.top_gate_capacitance * (top_gate_v
                                           - self.top_gate_offset_V)
        return (bottom + top) / E_CHARGE

    def carrier_densities(self, gate_v: float, T: float,
                          dirac_v: float | None = None,
                          top_gate_v: float = 0.0) -> tuple[float, float]:
        """Electron and hole densities (n, p) in m^-2, both positive."""
        n_cv = self.gate_density(gate_v, dirac_v, top_gate_v)
        n_0 = self.residual_density(T)
        root = math.sqrt(n_cv * n_cv + 4.0 * n_0 * n_0)
        return 0.5 * (n_cv + root), 0.5 * (-n_cv + root)

    # ------------------------------------------------------------------
    # heating: where the electrons end up when power goes in
    # ------------------------------------------------------------------
    def cooling_sigma(self, density: float) -> float:
        """Sigma in ``P/A = Sigma (Te^delta - T_l^delta)``, W m^-2 K^-delta.

        The supercollision coupling goes as the square of the density of
        states, which in graphene is linear in carrier density, so it is
        quoted at one density and scaled. Measured coefficients for
        graphene on an imperfect substrate are of order 1 W m^-2 K^-3 at
        n ~ 1e12 cm^-2.
        """
        n_ref = self.cooling_reference_density_cm2 * _CM2
        return self.cooling_coefficient * max(density, 1e14) / n_ref

    def electron_temperature(self, power_W: float, lattice_T: float,
                             density: float) -> float:
        """Electron temperature for a given absorbed power, K.

        Two stages in series, and they are not interchangeable:

        * the electrons sit above the lattice by the cooling law, which is
          what a hot-electron measurement is measuring;
        * the lattice itself sits above the bath by the substrate thermal
          resistance, which is the slower, more mundane path.

        Both DC Joule heating and absorbed light enter here identically.
        That is not a modelling convenience — it is the assumption behind
        calibrating absorbed optical power against DC power, so if the two
        did not share a channel the calibration would be measuring nothing.
        """
        if power_W <= 0.0:
            return lattice_T
        sigma = self.cooling_sigma(density) * self.channel_area_m2
        if sigma <= 0.0:
            return lattice_T
        delta = max(self.cooling_exponent, 1.0)
        return (lattice_T ** delta + power_W / sigma) ** (1.0 / delta)

    def absorptance(self, frequency_Hz: float, density: float) -> float:
        """Fraction of incident power the sheet absorbs.

        A flat interband term (pi*alpha = 2.3%, the universal value) plus a
        Drude term that grows with carrier density and rolls off above
        1/(2 pi tau). At sub-THz the Drude term dominates, which is why the
        photoresponse depends on where the gate is sitting.
        """
        omega_tau = 2.0 * math.pi * max(frequency_Hz, 0.0) \
            * self.drude_scattering_time_s
        n_ref = self.cooling_reference_density_cm2 * _CM2
        drude = 0.05 * (max(density, 0.0) / n_ref) / (1.0 + omega_tau ** 2)
        return self.thz_absorptance + drude

    # ------------------------------------------------------------------
    def phonon_resistivity(self, T: float) -> float:
        """Density-independent phonon resistivity, ohm/square."""
        if T <= 0.0:
            return 0.0
        rho_acoustic = self.rho_acoustic_per_K * T
        kT_meV = K_B * T / E_CHARGE * 1e3
        arg = self.spp_energy_meV / max(kT_meV, 1e-6)
        if arg > 700.0:                      # exp would overflow; term is 0
            rho_spp = 0.0
        else:
            rho_spp = self.spp_prefactor_ohm / (math.exp(arg) - 1.0)
        return rho_acoustic + rho_spp

    def mobility(self, density: float, T: float) -> float:
        """Mobility of one carrier species at density ``density`` (m^-2).

        Matthiessen's rule over three channels. The phonon and short-range
        terms enter as resistivities — they are density-independent in
        graphene — which makes the mobility they imply fall with density,
        exactly as measured.
        """
        density = max(density, 1e10)
        mu_imp = self.mobility_impurity_cm2Vs * _CM2_PER_VS
        rho_flat = self.phonon_resistivity(T) + self.rho_short_ohm
        inv = 1.0 / mu_imp + density * E_CHARGE * rho_flat
        return 1.0 / inv

    # ------------------------------------------------------------------
    def _classical_tensor(self, gate_v: float, B: float, T: float,
                          dirac_v: float | None = None,
                          top_gate_v: float = 0.0
                          ) -> tuple[float, float, float]:
        """Two-carrier Drude conductivity. Returns (sigma_xx, sigma_xy,
        n_net) in SI, with ``n_net = n - p`` signed."""
        n, p = self.carrier_densities(gate_v, T, dirac_v, top_gate_v)
        mu_n = self.mobility(n, T)
        mu_p = self.mobility(p, T)
        dn = 1.0 + (mu_n * B) ** 2
        dp = 1.0 + (mu_p * B) ** 2
        sigma_xx = E_CHARGE * (n * mu_n / dn + p * mu_p / dp)
        sigma_xy = E_CHARGE * B * (n * mu_n * mu_n / dn
                                   - p * mu_p * mu_p / dp)
        return sigma_xx, sigma_xy, n - p

    def _quantum_weight(self, n_net: float, B: float, T: float) -> float:
        """How completely Landau levels are resolved, 0 to 1.

        The product of the Lifshitz-Kosevich thermal factor and the Dingle
        factor, further suppressed near the Dirac point where puddles wash
        the levels out.
        """
        if not self.quantum_enabled:
            return 0.0
        absB = abs(B)
        absn = abs(n_net)
        if absB < 1e-4 or absn < 1e12:
            return 0.0
        m_c = HBAR * math.sqrt(math.pi * absn) / V_FERMI
        hbar_omega_c = HBAR * E_CHARGE * absB / m_c
        if hbar_omega_c <= 0.0:
            return 0.0
        X = 2.0 * math.pi ** 2 * K_B * T / hbar_omega_c
        r_thermal = 1.0 if X < 1e-6 else X / math.sinh(min(X, 700.0))
        dingle_arg = (2.0 * math.pi ** 2 * K_B * self.dingle_temperature_K
                      / hbar_omega_c)
        r_dingle = math.exp(-min(dingle_arg, 700.0))
        # quantisation survives only while the density is well clear of the
        # puddles that smear the Landau levels out
        n_0 = self.residual_density(T)
        puddle_factor = absn ** 2 / (absn ** 2 + n_0 ** 2)
        return max(0.0, min(1.0, r_thermal * r_dingle * puddle_factor))

    def resistivities(self, gate_v: float, B: float, T: float,
                      dirac_v: float | None = None,
                      top_gate_v: float = 0.0) -> tuple[float, float]:
        """Sheet resistivities (rho_xx, rho_xy) in ohm/square and ohm.

        This is the sample itself: no geometry, no contacts, no probe
        misalignment, no noise.
        """
        sigma_xx, sigma_xy, n_net = self._classical_tensor(
            gate_v, B, T, dirac_v, top_gate_v)

        w = self._quantum_weight(n_net, B, T)
        if w > 1e-6:
            absB = abs(B)
            # Shubnikov-de Haas: periodic in 1/B, frequency n h / 4e.
            # Minima at half-integer B_F/B is the Berry-phase-pi signature.
            b_f = abs(n_net) * H_PLANCK / (4.0 * E_CHARGE)
            osc = 0.5 * (1.0 + math.cos(2.0 * math.pi * b_f / absB))
            sigma_xx = sigma_xx * ((1.0 - w) + w * osc)

            # Hall plateaus at nu = +-4(N + 1/2) = +-2, +-6, +-10, ...
            #
            # The staircase has to be *smooth*: a floor() would make
            # sigma_xy jump between plateaus, which shows up as a vertical
            # cliff in R_xy(B) and as blocky wedges in a Landau fan. Write
            # the filling as u = nu/4 - 1/2, so plateau centres are at
            # integer u, and flatten u toward the nearest integer with a
            # window that vanishes exactly at the half-integer boundary:
            # the result is continuous, flat at the plateau centres, and
            # equal to the classical line where the plateaus hand over.
            nu_cl = n_net * H_PLANCK / (E_CHARGE * B)
            u = abs(nu_cl) / 4.0 - 0.5
            frac = u - round(u)
            u_q = u - frac * math.cos(math.pi * frac) ** 2
            nu_q = 4.0 * (u_q + 0.5)
            sign = 1.0 if sigma_xy >= 0.0 else -1.0
            sigma_xy_q = sign * nu_q * E_CHARGE ** 2 / H_PLANCK
            sigma_xy = sigma_xy * (1.0 - w) + w * sigma_xy_q

        if self.weak_localisation > 0.0:
            # An even-in-B correction to sigma_xx that vanishes by a few
            # times wl_field_T. Phenomenological, not an HLN fit.
            scale = self.weak_localisation * E_CHARGE ** 2 / (
                math.pi * H_PLANCK)
            sigma_xx -= scale / (1.0 + (B / self.wl_field_T) ** 2)

        denom = sigma_xx * sigma_xx + sigma_xy * sigma_xy
        if denom <= 0.0:
            return float("inf"), 0.0
        rho_xx = sigma_xx / denom
        rho_xy = -sigma_xy / denom      # electrons give rho_xy < 0 at B > 0
        return rho_xx, rho_xy

    # ------------------------------------------------------------------
    def resistances(self, gate_v: float, B: float, T: float,
                    dirac_v: float | None = None,
                    top_gate_v: float = 0.0) -> tuple[float, float]:
        """What a perfect 4-probe measurement of this Hall bar would read.

        ``R_xx`` carries the aspect ratio; ``R_xy`` does not (a Hall
        resistance is a sheet quantity). The probe misalignment is applied
        here rather than in :meth:`resistivities` because it is a property
        of the wiring, not of the graphene — and because a reader who
        symmetrises in B must be able to remove it.
        """
        rho_xx, rho_xy = self.resistivities(gate_v, B, T, dirac_v,
                                            top_gate_v)
        r_xx = rho_xx * self.aspect_ratio
        r_xy = rho_xy + self.hall_misalignment * r_xx
        return r_xx, r_xy

    def two_probe_resistance(self, gate_v: float, B: float, T: float,
                             dirac_v: float | None = None,
                             top_gate_v: float = 0.0) -> float:
        """Source-drain resistance including both contacts."""
        rho_xx, _ = self.resistivities(gate_v, B, T, dirac_v, top_gate_v)
        # the full channel is longer than the Vxx probe separation
        channel_squares = self.aspect_ratio * 1.6
        return rho_xx * channel_squares + 2.0 * self.contact_resistance_ohm

    def gate_leakage(self, gate_v: float, damaged: bool = False) -> float:
        """Gate leakage current, A. Grows exponentially; after oxide
        breakdown it is ohmic and enormous."""
        if damaged:
            return gate_v / 2.2e6          # a few microamps per volt
        ohmic = 2.0e-14 * gate_v
        arg = abs(gate_v) / self.leakage_voltage_V
        injected = self.leakage_scale_A * (math.expm1(min(arg, 60.0)))
        return ohmic + math.copysign(injected, gate_v)

    # ------------------------------------------------------------------
    def truth(self) -> dict:
        """The hidden parameters, for scoring a measurement against.

        Nothing in the driver layer may call this — it is the answer key.
        """
        out = asdict(self)
        out["oxide_capacitance_F_per_m2"] = self.oxide_capacitance
        out["density_per_volt_cm2"] = self.density_per_volt_cm2
        out["aspect_ratio"] = self.aspect_ratio
        return out
