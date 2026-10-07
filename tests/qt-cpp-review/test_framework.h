// Copyright (C) 2026 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause
// Test file for framework-only rules (--framework flag required). Rule ids are the
// FW- ids of references/qt-framework-checklist.md.
#pragma once

// FW-INC-6: qglobal.h (framework only)
#include <qglobal.h>

// FW-INC-1: bare Qt header without module prefix (framework only, header only)
#include <qstring.h>

// FW-INC-3: both qNN header and standard header included (framework only)
#include <q20algorithm>
#include <algorithm>

// FW-VAL-5: Q_DECLARE_METATYPE (framework only)
Q_DECLARE_METATYPE(MyType)
