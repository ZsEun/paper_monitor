#!/usr/bin/env python3
"""Test script to generate summary for a single paper"""

import sys
sys.path.insert(0, '/Users/sunze/Desktop/1_kiro/literature_boot/backend')

from app.services.ai_service import AIService

# Paper details from https://ieeexplore.ieee.org/document/11245616
title = "Theoretical Estimation on Maximum-to-Maximum Ratio of Radiated Emission From PCB With Attached Cable"

abstract = """This article presents a theoretical estimation method for the maximum-to-maximum ratio (MMR) of radiated emission (RE) from a printed circuit board (PCB) with an attached cable. The MMR is defined as the ratio of the maximum RE level to the minimum RE level when the cable position is varied. The proposed method is based on the equivalent dipole moment (EDM) model and the transmission line (TL) model. The EDM model is used to represent the PCB, and the TL model is used to represent the cable. The MMR is derived from the EDM and TL models, and the validity of the proposed method is confirmed by comparing the theoretical results with the measurement results. The proposed method can be used to estimate the MMR of RE from a PCB with an attached cable without performing measurements."""

# Initialize AI service
ai_service = AIService()

print("Testing NEW summary format (Problem, Idea, Result only):")
print(f"Title: {title}\n")
print("=" * 80)

# Generate summary
summary = ai_service.generate_summary(title, abstract)

print("\nGenerated Summary:")
print("=" * 80)
print(summary)
print("=" * 80)

# Check for brackets
if '[' in summary or ']' in summary:
    print("\n⚠️  WARNING: Brackets found in summary!")
else:
    print("\n✅ No brackets found - summary is clean!")
