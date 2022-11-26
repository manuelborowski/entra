/*! CellToggle 0.0.1
 * ©2021 Manuel Borowski
 */

/**
 * @summary     CellToggle
 * @description Creates a toggle button in a cell
 * @version     0.0.1
 *
 * This source file is free software, available under the following license:
 *   MIT license - http://datatables.net/license/mit
 *
 * This source file is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE. See the license files for details.
 *
 * For details please refer to: http://www.datatables.net
 */

export class MakeCellsToggleable {
    constructor(table, settings) {
        this.table = table.table();
        this.settings = settings;
        var _this = this

        // On cell click
        $(this.table.body()).on('click', 'td', function () {
            var currentColumnIndex = _this.table.cell(this).index().column;
            if (_this.settings.columns.includes(currentColumnIndex)) {

                var row = _this.table.row($(this).parents('tr'));
                var cell = _this.table.cell(this).node();
                var cell_content = _this.table.cell(this).data();
                var checked_found = $($.parseHTML(cell_content)).find("input:checkbox:checked").val();
                var current_value = typeof (checked_found) !== "undefined"
                var template = _this.get_toggle_template(!current_value);
                $(cell).html(template);
                _this.settings.onUpdate(table.cell(this), row, !current_value);
            }
        });
    }

    get_toggle_template(value) {
        return "<div class='custom-control custom-switch'><input type='checkbox' class='custom-control-input' onfocusout='$(this).updateEditableCell(this)' " + (value ? "checked" : "") + "></input><label class='custom-control-label' for='customSwitch1'></label></div>";
    }

    display() {
        var _this = this
        $.each(this.settings.columns, function (ci, cv) {
            $.each(_this.table.column(cv).data(), function (ri, rv) {
                var template = _this.get_toggle_template(rv);
                _this.table.cell({row: ri, column: cv}).data(template)
            })
        });
    }
}

