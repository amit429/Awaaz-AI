from app.config import Settings
from app.providers import sarvam


def test_needs_transliteration():
    assert sarvam.needs_transliteration("Theek hai")
    assert not sarvam.needs_transliteration("ठीक है, ₹420।")


async def test_unchanged_in_mock_mode_without_key_or_when_native():
    assert (
        await sarvam.transliterate("Theek hai", Settings(mock_providers=True, sarvam_api_key="k"))
        == "Theek hai"
    )
    assert (
        await sarvam.transliterate("Theek hai", Settings(mock_providers=False, sarvam_api_key=""))
        == "Theek hai"
    )
    assert (
        await sarvam.transliterate("ठीक है", Settings(mock_providers=False, sarvam_api_key="k"))
        == "ठीक है"
    )
