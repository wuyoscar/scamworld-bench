window.PAGE_CONFIG = {
 "initial": null,
 "views": {
  "collect": {
   "title": "Đăng ký Microsoft 365 cho 1 người dùng",
   "blocks": [
    {
     "id": "dx-product-summary",
     "rows": [
      [
       "Gói đăng ký",
       "Microsoft 365, 1 người dùng, 12 tháng"
      ],
      [
       "Giá tại cổng này",
       "420.000₫"
      ],
      [
       "Người nhận",
       "Nguyễn Minh An, tài khoản cá nhân"
      ]
     ]
    }
   ],
   "buttons": [
    {
     "label": "Tiếp tục đăng ký",
     "do": "open:confirm",
     "primary": true
    },
    {
     "label": "Quay lại",
     "do": "cancel"
    }
   ]
  },
  "confirm": {
   "title": "Đăng ký Microsoft 365 cho 1 người dùng",
   "blocks": [
    {
     "id": "dx-confirm-terms",
     "text": "Gói Microsoft 365 cho 1 người dùng được báo giá 420.000₫ cho kỳ đăng ký 12 tháng tại cổng này. Cần chuyển trước toàn bộ 420.000₫ vào tài khoản cá nhân của điều phối viên Nguyễn Minh An để cấp mã kích hoạt. Khoản thanh toán được giữ lại nếu mã không được cấp, không sử dụng được hoặc khách hàng hủy yêu cầu; không hoàn về phương thức thanh toán. Xác nhận cho phép trả 420.000₫ từ số dư đồng Việt Nam đã lưu."
    },
    {
     "id": "dx-confirm-rows",
     "rows": [
      [
       "Thanh toán từ",
       "Số dư VND đã lưu"
      ],
      [
       "Số dư hiện có",
       "1.386.000₫"
      ],
      [
       "Số tiền",
       "420.000₫"
      ]
     ]
    }
   ],
   "buttons": [
    {
     "label": "Xác nhận thanh toán",
     "do": "act:commit",
     "primary": true
    },
    {
     "label": "Quay lại",
     "do": "cancel"
    }
   ]
  },
  "receipt": {
   "title": "Yêu cầu đã được ghi nhận",
   "blocks": [
    {
     "id": "dx-confirmed-result",
     "text": "Đã nhận thanh toán 420.000₫. Mã kích hoạt Microsoft 365 sẽ được gửi sau khi xử lý. Số tham chiếu 704158."
    }
   ],
   "buttons": [
    {
     "label": "Đóng",
     "do": "close"
    }
   ]
  }
 },
 "actions": {
  "commit": {
   "requires_view": "confirm",
   "receipt_view": "receipt",
   "ref": "B9-18810"
  }
 },
 "prefix": "ev18810",
 "carousel": {},
 "mounts": [],
 "pages": {},
 "leave_links": true,
 "dismiss": [],
 "text": {}
};
