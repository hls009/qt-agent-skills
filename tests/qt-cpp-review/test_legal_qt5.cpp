// Copyright (C) 2026 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause
// Legal Qt 5.15 code: the linter must raise NO finding against this file.

// Each block below is a claim this skill set makes about Qt 5.15, so the fixture is the
// counterweight to the QT6-* bans — a rule that fires here is a false positive against
// code the same repository tells a reviewer to leave alone. run_tests.py Test 4 asserts
// that no finding is produced at all.

#include <QtWidgets>

// Text API that looks Qt 6 but is Qt 5.15 (qt515-deltas.md "do not flag").
void textShapes(QStringView view, qsizetype count, const QString &text)
{
    const QString::SplitBehavior keep = Qt::KeepEmptyParts;
    const QStringList parts = text.split(QLatin1Char(','), keep);
    const QString hex = QColor(Qt::red).name(QColor::HexArgb);
    const QString iconName = QIcon().name();
    Q_UNUSED(view); Q_UNUSED(count); Q_UNUSED(parts); Q_UNUSED(hex); Q_UNUSED(iconName);
}

// Meta-type access: fromType<T>() is Qt 5.15 (qmetatype.h), userType() and the
// string lookup are the older routes. None of them is a finding.
int metaTypeIds()
{
    const int a = QMetaType::fromType<QString>().id();
    const int b = QVariant().userType();
    const int c = QMetaType::type("QStringList");
    return a + b + c;
}

// Events: QWheelEvent has position()/globalPosition() since 5.15; QMouseEvent does
// not, and still uses pos(). QT6-4 has to tell the two apart by context.
class WheelSpin : public QWidget {
    Q_OBJECT
public:
    explicit WheelSpin(QWidget *parent = nullptr) : QWidget(parent) {}

protected:
    void wheelEvent(QWheelEvent *event) override {
        const QPointF where = event->position();
        const QPointF global = event->globalPosition();
        setAngle(qRound(where.x() + global.y()));
    }
    void mousePressEvent(QMouseEvent *mouseEvent) override {
        setAngle(mouseEvent->pos().x());
    }
    void resizeEvent(QResizeEvent *) override { update(); }

private:
    void setAngle(int degrees) { m_angle = degrees; update(); }
    int m_angle = 0;
};

// Item views: setCurrentRow() and setCurrentSection() do exist in Qt 5, just not on
// QAbstractItemView. The ban is about a view's setCurrentSection().
void legalSelection(QListWidget *list, QTableView *view, QDateTimeEdit *edit)
{
    list->setCurrentRow(1);
    view->setCurrentIndex(view->model()->index(2, 3));
    view->selectRow(2);
    view->selectColumn(3);
    edit->setCurrentSection(QDateTimeEdit::MinuteSection);
}

// Timers and proxy refresh. callOnTimeout is Qt 5.14+; the proxy has invalidate()
// and invalidateFilter(), and Qt 6's invalidateLayout() is deliberately absent here.
void timersAndProxy(QSortFilterProxyModel *proxy)
{
    QTimer::callOnTimeout(100, [] {});
    proxy->invalidate();
    proxy->invalidateFilter();
}
