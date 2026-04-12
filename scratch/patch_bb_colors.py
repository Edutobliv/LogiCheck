with open('core/yolo_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = (
    '            if lookup in self.tracking_data:\n'
    '                for x1, y1, x2, y2, track_id, ui_cat in self.tracking_data[lookup]:\n'
    '                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)\n'
    '                    tid_str = f"ID:{track_id}" if track_id is not None else "ID:--"\n'
    '                    cv2.putText(frame, f"{tid_str} {ui_cat}", (x1, max(y1 - 5, 10)),\n'
    '                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)\n'
)

new_block = (
    '            if lookup in self.tracking_data:\n'
    '                _cat_colors = {\n'
    '                    "Cemento":           ( 50, 200,  80),\n'
    '                    "Tuberia Presion":   (255, 160,   0),\n'
    '                    "Tuberia Sanitaria": ( 30, 144, 255),\n'
    '                }\n'
    '                for x1, y1, x2, y2, track_id, ui_cat in self.tracking_data[lookup]:\n'
    '                    color = _cat_colors.get(ui_cat, (0, 255, 0))\n'
    '                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)\n'
    '                    tid_str = f"ID:{track_id}" if track_id is not None else "ID:--"\n'
    '                    label   = f"{tid_str} {ui_cat}"\n'
    '                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)\n'
    '                    cv2.rectangle(frame, (x1, max(y1-18, 0)), (x1+tw+4, max(y1, 18)), color, -1)\n'
    '                    cv2.putText(frame, label, (x1+2, max(y1-4, 14)),\n'
    '                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)\n'
)

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('core/yolo_manager.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
else:
    print('BLOCK NOT FOUND - checking actual content:')
    idx = content.find('for x1, y1, x2, y2, track_id, ui_cat in self.tracking_data[lookup]')
    print(repr(content[max(0, idx-200):idx+300]))
