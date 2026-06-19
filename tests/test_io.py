import pytest

from desi_rv_audit.io import load_one


def test_strict_fits_loader_rejects_misaligned_fibermap(tmp_path):
    fits = pytest.importorskip("astropy.io.fits")
    path = tmp_path / "rvpix_exp-main-backup.fits"

    rvtab = fits.BinTableHDU.from_columns(
        [
            fits.Column(name="TARGETID", format="K", array=[1, 2]),
            fits.Column(name="VRAD", format="D", array=[10.0, 11.0]),
            fits.Column(name="VRAD_ERR", format="D", array=[1.0, 1.0]),
            fits.Column(name="SN_R", format="D", array=[10.0, 10.0]),
            fits.Column(name="RVS_WARN", format="K", array=[0, 0]),
            fits.Column(name="SUCCESS", format="L", array=[True, True]),
            fits.Column(name="EXPID", format="K", array=[100, 101]),
            fits.Column(name="FIBER", format="K", array=[1, 2]),
            fits.Column(name="VSINI", format="D", array=[1.0, 1.0]),
            fits.Column(name="RR_SPECTYPE", format="4A", array=["STAR", "STAR"]),
        ],
        name="RVTAB",
    )
    fibermap = fits.BinTableHDU.from_columns(
        [
            fits.Column(name="TARGETID", format="K", array=[1, 999]),
            fits.Column(name="EXPID", format="K", array=[100, 101]),
            fits.Column(name="FIBER", format="K", array=[1, 2]),
            fits.Column(name="MJD", format="D", array=[1.0, 2.0]),
            fits.Column(name="NIGHT", format="K", array=[20210101, 20210102]),
            fits.Column(name="FIBERSTATUS", format="K", array=[0, 0]),
            fits.Column(name="TILEID", format="K", array=[10, 10]),
        ],
        name="FIBERMAP",
    )
    gaia = fits.BinTableHDU.from_columns(
        [fits.Column(name="SOURCE_ID", format="K", array=[10, 20])],
        name="GAIA",
    )
    fits.HDUList([fits.PrimaryHDU(), rvtab, fibermap, gaia]).writeto(path)

    with pytest.raises(ValueError, match="row-alignment mismatch"):
        load_one(path, strict_desi_main=True)
