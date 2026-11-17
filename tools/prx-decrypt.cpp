// SPDX-License-Identifier: GPL-2.0-or-later
// Thin local bridge to the pinned pspdecrypt PRX implementation.
#include "PrxDecrypter.h"
extern "C" __declspec(dllexport) int decrypt_prx(
    const unsigned char *input, unsigned char *output, unsigned int size) {
    if (!input || !output || size < 0x150) return -100;
    return pspDecryptPRX(input, output, size, nullptr, true);
}
