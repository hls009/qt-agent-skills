# Model/View and delegate rules (Qt 5 Widgets)

Checklist for the Model/View Contracts agent. Qt 5 classes: `QAbstractItemModel`,
`QAbstractListModel`, `QAbstractTableModel`, `QSortFilterProxyModel`,
`QStyledItemDelegate`, `QItemSelectionModel`, and the item views.

IDs are `MV-*` for prose findings; the linter covers the mechanically detectable
subset as `MDL-*`.

## The signal protocol

- **MV-1**: Every structural change is bracketed by the matching begin/end pair —
  `beginInsertRows`/`endInsertRows`, `beginRemoveRows`/`endRemoveRows`,
  `beginMoveRows`/`endMoveRows`, `beginResetModel`/`endResetModel`. A `layoutChanged()`
  or `dataChanged()` is **not** a substitute; views keep stale index maps and crash on
  the next `index()`.
- **MV-2**: No early `return`, exception, or `qDebug()`-and-bail between a begin/end
  pair. Guard first, then open the bracket.
- **MV-3**: `beginInsertRows(parent, first, last)` uses the parent index and the child
  row range *before* the insertion; `beginRemoveRows` likewise before removal. `last` is
  inclusive: inserting one row at index 2 is `(parent, 2, 2)`.
- **MV-4**: Removing all rows from an empty model produces `first > last`, which violates
  the contract: guard with `if (rows.isEmpty()) return;` before
  `beginRemoveRows(parent, 0, count - 1)`.
- **MV-5**: `beginMoveRows`'s `destinationChild` must not lie inside the moved range;
  the common off-by-one is moving a row down without adjusting for the hole it leaves.
- **MV-6**: Structural changes never happen outside the model's own thread.
- **MV-7**: `reset()` (deprecated in favour of the begin/end reset pair) is a full-view
  invalidation — expensive and it discards selection and expanded state. Prefer targeted
  insert/remove/change calls.

## data(), roles, and flags

- **MV-8**: `data()` handles every role that `roleNames()` advertises. A `default:` that
  returns `{}` for an unhandled role is a silent blank cell. (Linter: MDL-7.)
- **MV-9**: `roleNames()` maps `Qt::UserRole + 1` and above to names that exist and do
  not collide with the built-in roles. Cache the `QHash` — rebuilding per call is the
  usual cause of slow view setup with thousands of rows.
- **MV-10**: `Qt::DisplayRole` returns a displayable type (string/number/date); `Qt::DecorationRole`
  a `QIcon`/`QPixmap`; `Qt::ToolTipRole` a string; `Qt::TextAlignmentRole` an alignment
  value (or a `Qt::Alignment`), `Qt::SizeHintRole` a `QSize`.
- **MV-11**: `setData()` returns `true` only when it changed something *and* emitted
  `dataChanged` for the affected roles. Returning `true` silently is a data-loss bug.
- **MV-12**: `flags()` starts from the base implementation (`QAbstractItemModel::flags(index)`
  or `Qt::ItemIsEnabled | Qt::ItemIsSelectable`) and adds/removes selectively; returning a
  bare `Qt::ItemIsEditable` drops selection.
- **MV-13**: `headerData()` is implemented for the orientations the view shows, including
  `Qt::Horizontal` sections when `QTableView::horizontalHeader()` is visible.
- **MV-14**: `dataChanged` passes the changed roles. An empty roles vector means "all
  roles" and forces a full delegate repaint — it is the linter's MDL-2 for a reason.
- **MV-15**: Column/row counts stay consistent with the container the model indexes;
  `rowCount(parent)` returns 0 for a parent that has no children, and for a table model it
  must ignore the `column` argument's neighbours rather than guess.

## Index validity

- **MV-16**: `QModelIndex` objects are handles to a *snapshot*. Never store one as a
  member across insertions, sorting or filtering; use `QPersistentModelIndex` when the
  intent really is "track this item", and check `isValid()` on use.
- **MV-17**: An index from the source model is not valid for the proxy, and vice versa.
  `mapToSource()`/`mapFromSource()` are the only bridge, and both are invalidated by any
  structural change in either model.
- **MV-18**: Every `index(row, column, parent)` is matched by `parent(index)` returning
  the same parent, and `hasChildren()`/`canFetchMore()`/`fetchMore()` agree with the tree
  you actually expose. Mismatch here produces expandable-but-empty nodes.

## Sorting, filtering, editing

- **MV-19**: `QSortFilterProxyModel::setDynamicSortFilter(true)` re-filters on every
  `dataChanged`/`rowsInserted`; for a large model set it `false` and call
  `invalidateFilter()`/`invalidate()` explicitly at a coarse point (and say which).
  Qt 5 declares `QSortFilterProxyModel::invalidate()` and `invalidateFilter()`
  (`qsortfilterproxymodel.h`) and nothing else of the kind: `invalidateLayout()` and
  `invalidateRows()` are Qt 6, so either one is a compile error here, not a style
  difference.
- **MV-20**: `lessThan()` compares the same role the view sorts on
  (`sortRole()`), and is strict weak ordering — returning `true` for equal values breaks
  the sort. Use `QString::localeAwareCompare()` for user-visible text, not `operator<`,
  which is case-sensitive and code-point ordered.
- **MV-21**: `filterKeyColumn()` applies to the role chosen by `setFilterRole()`; filtering
  `Qt::DisplayRole` while the user searches an internal id role silently matches nothing.
- **MV-22**: `Qt::ItemIsEditable` implies an editor: a `QStyledItemDelegate` subclass must
  implement `createEditor`, `setEditorData`, `setModelData` (and `updateEditorGeometry`),
  or edits do nothing. `setModelData` that forgets `model->setData()` is the usual cause.
- **MV-23**: A delegate that customises painting calls the base `paint()` first (or
  reproduces selection/focus/disabled states), otherwise the row loses its selection
  highlight.
- **MV-24**: `sizeHint()` in a delegate returns a hint that accounts for the icon and the
  font of the row it is given, not a constant — with `QTableView::resizeRowsToContents()`
  a wrong `sizeHint` is visible as clipped text.
- **MV-25**: `commitData`/`closeEditor` are connected where an editor must end its session
  on a button action (e.g. a `QDialogButtonBox`-driven editor); otherwise the model only
  sees the value after focus loss.
- **MV-26**: `QItemSelectionModel` signals (`selectionChanged`) fire with `selected` and
  `deselected` ranges; handlers that assume "one row changed" break on Shift/click
  ranges.

## Views and models wiring

- **MV-27**: Views are created and destroyed only on the GUI thread; a model owned by a
  worker thread must expose changes through queued signals, not by calling
  `beginInsertRows` from that thread.
- **MV-28**: `setModel()` on an already-wired view requires `QAbstractItemModel`
  ownership to stay stable; re-parenting the model afterwards can delete it while views
  still reference it.
- **MV-29**: `QItemSelectionModel` is created by the first view; code that constructs its
  own selection model for the same view ends up with two competing ones.
- **MV-30**: `QTableView::setColumnWidth`/`horizontalHeader()->setSectionResizeMode`
  conflict with `resizeColumnsToContents()` — pick a policy. In Qt 5 the enum spelling is
  `QHeaderView::ResizeMode` (`QHeaderView::Interactive`, `…::Stretch`) — the Qt 6
  `QHeaderView::ResizeMode::Interactive` scoped form is not available.
- **MV-31**: Item views with very large models: `setUniformItemSizes(true)`,
  `setVerticalScrollMode(QAbstractItemView::ScrollPerPixel)` only when heights are
  uniform, and avoid `resizeRowsToContents()` on every data change (it walks every row).

## Cache and invalidation

- **MV-32**: Any member cache inside a model (`m_searchCache`, `m_filteredRows`, row
  offsets) must be invalidated in every structural path — insert, remove, move, reset,
  and `setData`. The classic symptom is a stale row after a filter change.
- **MV-33**: A model that wraps a container keeps **one** owner of that container. Two
  index spaces (the vector and a parallel row map) that can drift is MV-32 in disguise.
