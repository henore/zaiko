// static/js/main.js
let table;
let selectedProduct = null;

$(document).ready(function() {
   table = $('#productTable').DataTable({
       ajax: {
           url: '/products',
           dataSrc: ''
       },
       columns: [
           { data: 'name' },
           { data: 'color' },
           { data: 'size' },
           { data: 'quantity' }
       ],
       order: [[0, 'asc'], [1, 'asc']],

    rowCallback: function(row, data) {
        let productGroups = {};
        let groupCount = 0;
        this.api().rows().data().each(function(rowData) {
            if (!productGroups[rowData.name]) {
                productGroups[rowData.name] = groupCount++;
            }
        });
        $(row).css('background-color',
            productGroups[data.name] % 2 ? '#E8F5E9' : '#F3E5F5'
        );
    },
       pageLength: -1,
       lengthMenu: [[-1], ["全て"]],
       language: {
           url: '//cdn.datatables.net/plug-ins/1.10.25/i18n/Japanese.json'
       }
   });

    // 行選択のイベントリスナー
    $('#productTable tbody').on('click', 'tr', function() {
        if ($(this).hasClass('selected')) {
            $(this).removeClass('selected');
            selectedProduct = null;
            $('#updateStockBtn, #reduceStockBtn').prop('disabled', true);
        } else {
            table.$('tr.selected').removeClass('selected');
            $(this).addClass('selected');
            selectedProduct = table.row(this).data();
            $('#updateStockBtn, #reduceStockBtn').prop('disabled', false);
        }
    });

   // 新規商品登録
   $('#addProductBtn').click(function() {
       const formData = {};
       $('#addProductForm').serializeArray().forEach(item => {
           formData[item.name] = item.value;
       });
       formData.quantity = parseInt(formData.quantity);

       $.ajax({
           url: '/add_product',
           type: 'POST',
           contentType: 'application/json',
           data: JSON.stringify(formData),
           success: function(response) {
               if (response.success) {
                   $('#addProductModal').modal('hide');
                   table.ajax.reload();
                   $('#addProductForm')[0].reset();
               } else {
                   alert('エラーが発生しました: ' + response.error);
               }
           }
       });
   });

    // 在庫追加ボタンのイベント
    $('#updateStockBtn').click(function() {
        if (selectedProduct) {
            $('#selectedProduct').text(
                `商品: ${selectedProduct.name} - ${selectedProduct.color}` +
                (selectedProduct.size ? ` - ${selectedProduct.size}` : '')
            );
            $('#updateStockModal').modal('show');
        }
    });

    // 売上登録ボタンのイベント
    $('#reduceStockBtn').click(function() {
        if (selectedProduct) {
            $('#selectedProductForSale').text(
                `商品: ${selectedProduct.name} - ${selectedProduct.color}` +
                (selectedProduct.size ? ` - ${selectedProduct.size}` : '')
            );
            $('#saleModal').modal('show');
        }
    });

    //在庫追加
    $('#updateStockConfirmBtn').click(function() {
        const quantity = parseInt($('#stockQuantity').val());
        console.log('Data being sent:', {  // デバッグ用
            name: selectedProduct.name,
            color: selectedProduct.color,
            size: selectedProduct.size,
            quantity: quantity
        });

        $.ajax({
            url: '/update_stock',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: selectedProduct.name,
                color: selectedProduct.color,
                size: selectedProduct.size,
                quantity: quantity
            }),
            success: function(response) {
                if (response.success) {
                    $('#updateStockModal').modal('hide');
                    table.ajax.reload();
                    $('#stockQuantity').val('');
                } else {
                    alert('エラーが発生しました: ' + response.error);
                }
            }
        });
    });

    // 売上登録処理
    $('#saleConfirmBtn').click(function() {
        const quantity = parseInt($('#saleQuantity').val());
        const price = parseInt($('#salePrice').val());
        const shipping = parseInt($('#shippingFee').val())
        const bundleId = $('#bundleId').val();

        $.ajax({
            url: '/register_sale',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: selectedProduct.name,
                color: selectedProduct.color,
                size: selectedProduct.size,
                quantity: quantity,
                price: price,
                shipping_fee: shipping,
                bundle_id: bundleId
            }),
            success: function(response) {
                if (response.success) {
                    $('#saleModal').modal('hide');
                    table.ajax.reload();
                    $('#saleQuantity, #salePrice, #bundleId, #shippingFee').val('');
                } else {
                    alert('エラーが発生しました: ' + response.error);
                }
            }
        });
    });

       // テーブルの行をダブルクリックで編集モーダル表示
    $('#productTable tbody').on('dblclick', 'tr', function() {
        const data = table.row(this).data();
        $('#editProductForm input[name="new_name"]').val(data.name);
        $('#editProductForm input[name="new_color"]').val(data.color);
        $('#editProductForm input[name="new_size"]').val(data.size);
        $('#editProductModal').data('oldData', data).modal('show');
    });

    // 編集実行
    $('#editProductBtn').click(function() {
        const oldData = $('#editProductModal').data('oldData');
        const formData = {
            old_name: oldData.name,
            old_color: oldData.color,
            old_size: oldData.size,
            new_name: $('#editProductForm input[name="new_name"]').val(),
            new_color: $('#editProductForm input[name="new_color"]').val(),
            new_size: $('#editProductForm input[name="new_size"]').val()
        };

        $.ajax({
            url: '/edit_product',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function(response) {
                if (response.success) {
                    $('#editProductModal').modal('hide');
                    table.ajax.reload();
                } else {
                    alert('エラーが発生しました: ' + response.error);
                }
            }
        });
    });
});