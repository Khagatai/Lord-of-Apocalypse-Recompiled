/* SPDX-License-Identifier: GPL-3.0-or-later
 * Native launcher settings page. Persistence stays in graphics_settings.py. */
static const wchar_t *settings_tab_names[]={L"Graphics",L"Display",L"Advanced",L"Language",L"Controls"};
static const int settings_tab_items[4][5]={{1,4,7,8,14},{2,3,5,6,-1},{9,10,11,12,13},{0,-1,-1,-1,-1}};
static int settings_dirty(void){return settings_loaded&&memcmp(settings_codes,settings_saved,sizeof settings_codes)!=0;}
static void settings_text(const char *in,wchar_t *out,int capacity){if(!MultiByteToWideChar(CP_UTF8,0,in,-1,out,capacity))out[0]=0;}
static void settings_fonts(void){
    HWND buttons[]={settings_button,settings_back,settings_save};
    for(unsigned i=0;i<sizeof buttons/sizeof buttons[0];i++)if(buttons[i])SendMessageW(buttons[i],WM_SETFONT,(WPARAM)font,TRUE);
    for(int i=0;i<5;i++)if(settings_tabs[i])SendMessageW(settings_tabs[i],WM_SETFONT,(WPARAM)font,TRUE);
    for(int i=0;i<LOA_SETTINGS_COUNT;i++)if(settings_rows[i])SendMessageW(settings_rows[i],WM_SETFONT,(WPARAM)font,TRUE);
    for(int i=0;i<3;i++)if(preset_buttons[i])SendMessageW(preset_buttons[i],WM_SETFONT,(WPARAM)font,TRUE);
}
static HWND settings_new_button(HWND parent,int id,const wchar_t *text){
    HWND h=CreateWindowW(L"BUTTON",text,WS_CHILD|WS_TABSTOP|BS_OWNERDRAW,0,0,0,0,parent,(HMENU)(INT_PTR)id,NULL,NULL);
    SetWindowLongPtrW(h,GWLP_WNDPROC,(LONG_PTR)styled_button_proc);return h;
}
static void settings_create(HWND parent){
    settings_back=settings_new_button(parent,ID_SETTINGS_BACK,L"Back");settings_save=settings_new_button(parent,ID_SETTINGS_SAVE,L"Save settings");
    for(int i=0;i<5;i++)settings_tabs[i]=settings_new_button(parent,ID_SETTINGS_TAB+i,settings_tab_names[i]);
    for(int i=0;i<LOA_SETTINGS_COUNT;i++){
        wchar_t text[128];settings_text(loa_setting_labels[i],text,128);settings_rows[i]=settings_new_button(parent,ID_SETTING_ROW+i,text);
    }
    const wchar_t *presets[]={L"Original",L"Balanced",L"High Quality"};
    for(int i=0;i<3;i++)preset_buttons[i]=settings_new_button(parent,ID_PRESET+i,presets[i]);
}
static void settings_layout(void){
    int x=content_x(),w=content_width();
    ShowWindow(settings_back,settings_page?SW_SHOW:SW_HIDE);ShowWindow(settings_save,settings_page?SW_SHOW:SW_HIDE);
    EnableWindow(settings_back,!child);EnableWindow(settings_save,!child&&settings_dirty());
    SetWindowTextW(settings_back,settings_dirty()?L"Cancel":L"Back");
    MoveWindow(settings_back,x,vertical(490),px(90),vertical(34),TRUE);
    MoveWindow(settings_save,x+w-px(148),vertical(490),px(148),vertical(34),TRUE);
    int gap=px(4),tab_width=(w-gap*4)/5;
    for(int i=0;i<5;i++){
        MoveWindow(settings_tabs[i],x+i*(tab_width+gap),vertical(198),tab_width,vertical(34),TRUE);
        ShowWindow(settings_tabs[i],settings_page?SW_SHOW:SW_HIDE);EnableWindow(settings_tabs[i],!child&&settings_loaded);
    }
    for(int i=0;i<LOA_SETTINGS_COUNT;i++){
        if(settings_loaded){char text[256];wchar_t visible[256];snprintf(text,sizeof text,"%s: %s",loa_setting_labels[i],loa_setting_values[i][settings_codes[i]]);settings_text(text,visible,256);SetWindowTextW(settings_rows[i],visible);}
        ShowWindow(settings_rows[i],SW_HIDE);
    }
    if(settings_page&&settings_tab<4){
        for(int row=0;row<5;row++){
            int i=settings_tab_items[settings_tab][row];if(i<0)continue;
            MoveWindow(settings_rows[i],x,vertical(244+row*43),w,vertical(38),TRUE);
            ShowWindow(settings_rows[i],SW_SHOW);EnableWindow(settings_rows[i],!child&&settings_loaded&&!(i==3&&settings_codes[2]));
        }
    }
    for(int i=0;i<3;i++){
        int width=(w-px(16))/3;MoveWindow(preset_buttons[i],x+i*(width+px(8)),vertical(317),width,vertical(38),TRUE);
        ShowWindow(preset_buttons[i],settings_page&&settings_tab==3?SW_SHOW:SW_HIDE);EnableWindow(preset_buttons[i],!child&&settings_loaded);
    }
}
static void settings_paint(HDC dc,int x,int width){
    RECT title={x,vertical(94),x+width,vertical(141)};label(dc,title_font,INK,title,L"Settings",DT_SINGLELINE|DT_VCENTER);
    if(settings_tab==4){
        wchar_t copy[4096];wcscpy(copy,settings_controls);wchar_t *current=copy;int y=247,row=0;
        while(current&&*current){
            wchar_t *next=wcschr(current,L'\n');if(next)*next++=0;
            wchar_t *split=wcsstr(current,L"  ");
            if(split){
                *split=0;split++;while(*split==L' ')split++;
                RECT left={x+px(4),vertical(y),x+width/2,vertical(y+25)},right={x+width/2,vertical(y),x+width-px(4),vertical(y+25)};
                label(dc,font,MUTED,left,current,DT_SINGLELINE|DT_VCENTER);label(dc,font,INK,right,split,DT_SINGLELINE|DT_VCENTER|DT_RIGHT);y+=25;
            }else if(*current){
                RECT text={x+px(4),vertical(y),x+width-px(4),vertical(y+18)};
                label(dc,small_font,row==0?GOLD:MUTED,text,current,DT_SINGLELINE|DT_VCENTER);y+=row==0?23:16;
            }else y+=6;
            row++;current=next;
        }
    }
    if(settings_tab==3){
        RECT info={x,vertical(374),x+width,vertical(447)};
        label(dc,font,MUTED,info,L"Versions keep separate saves.\nJapanese voices and music stay unchanged.",DT_WORDBREAK);
    }
    const wchar_t *notes[]={L"Movies keep their original timing. FPS changes apply on launch.",L"Window resolution is used in windowed mode.",L"The optional HD pack builds on Play and may take hours.",L"Presets keep the selected language.",L"Control bindings are shown for reference."};
    RECT foot={x,vertical(465),x+width,vertical(483)};label(dc,small_font,MUTED,foot,notes[settings_tab],DT_SINGLELINE|DT_VCENTER);
    RECT hint={x,vertical(534),x+width,vertical(554)};
    label(dc,small_font,MUTED,hint,L"The same preferences are available in the in-game F1 menu.",DT_SINGLELINE|DT_VCENTER);
}
static int settings_draw_button(const DRAWITEMSTRUCT *item){
    int id=(int)item->CtlID;
    if(!((id>=ID_SETTINGS_TAB&&id<ID_SETTINGS_TAB+5)||(id>=ID_SETTING_ROW&&id<ID_SETTING_ROW+LOA_SETTINGS_COUNT)||(id>=ID_PRESET&&id<ID_PRESET+3)||id==ID_SETTINGS_SAVE))return 0;
    RECT r=item->rcItem;HDC dc=item->hDC;int disabled=(item->itemState&ODS_DISABLED)!=0,hover=hover_button==item->hwndItem;
    int selected=id>=ID_SETTINGS_TAB&&id<ID_SETTINGS_TAB+5&&id-ID_SETTINGS_TAB==settings_tab;
    int primary=selected||id==ID_SETTINGS_SAVE;fill(dc,r,BG);
    COLORREF fill_color=primary?(disabled?RGB(75,75,67):GOLD):hover?RGB(27,38,52):PANEL;
    box(dc,r,fill_color,primary?fill_color:EDGE,8);
    COLORREF color=disabled?RGB(113,124,139):primary?RGB(29,28,24):INK;
    if(id>=ID_SETTING_ROW&&id<ID_SETTING_ROW+LOA_SETTINGS_COUNT){
        int index=id-ID_SETTING_ROW;wchar_t text[160];settings_text(loa_setting_labels[index],text,160);
        RECT left=r;left.left+=px(12);left.right=r.left+(r.right-r.left)*55/100;
        label(dc,font,color,left,text,DT_SINGLELINE|DT_VCENTER|DT_END_ELLIPSIS);
        RECT right=r;right.left=left.right;right.right-=px(12);settings_text(loa_setting_values[index][settings_codes[index]],text,160);
        label(dc,font,disabled?MUTED:GOLD,right,text,DT_RIGHT|DT_SINGLELINE|DT_VCENTER|DT_END_ELLIPSIS);
    }else{
        wchar_t text[80];GetWindowTextW(item->hwndItem,text,80);label(dc,font,color,r,text,DT_CENTER|DT_SINGLELINE|DT_VCENTER);
    }
    if(item->itemState&ODS_FOCUS)focus_frame(dc,r,primary?RGB(145,119,70):MUTED);
    return 1;
}
static void settings_changed(void){
    set_status(settings_dirty()?L"Unsaved changes. Save to use these settings on your next launch.":L"These settings are shared with the in-game menu.",0);
    layout();RedrawWindow(main_window,NULL,NULL,RDW_INVALIDATE|RDW_ALLCHILDREN|RDW_UPDATENOW);
}
static void settings_change(int index,int direction){
    if(!settings_page||!settings_loaded||child||index<0||index>=LOA_SETTINGS_COUNT)return;
    if(index==3&&settings_codes[2])return;
    int next=settings_codes[index]+direction;
    if(direction==0)next=(settings_codes[index]+1)%loa_setting_lengths[index];
    if(next<0||next>=loa_setting_lengths[index])return;
    settings_codes[index]=next;settings_changed();
}
static void settings_request(int save){
    wchar_t python[32768],script[32768],command[32768]={0};size_t used=0;
    swprintf(python,32768,L"%ls\\private\\tools\\python314\\python.exe",root);swprintf(script,32768,L"%ls\\tools\\launcher_settings.py",root);
    int ok=argument(command,32768,&used,python)&&argument(command,32768,&used,L"-u")&&argument(command,32768,&used,script)&&argument(command,32768,&used,save?L"--save":L"--read");
    if(save){
        for(int i=0;i<LOA_SETTINGS_COUNT;i++){wchar_t code[16];swprintf(code,16,L"%d",settings_codes[i]);ok=ok&&argument(command,32768,&used,code);}
        wchar_t token[65];MultiByteToWideChar(CP_UTF8,0,settings_token,-1,token,65);ok=ok&&argument(command,32768,&used,L"--expected")&&argument(command,32768,&used,token);
    }
    if(!ok){set_status(L"The settings command is too long.",1);return;}
    SECURITY_ATTRIBUTES security={sizeof security,NULL,TRUE};HANDLE write_pipe=NULL;
    if(!CreatePipe(&read_pipe,&write_pipe,&security,0)){set_status(L"Could not open the settings helper.",1);return;}
    SetHandleInformation(read_pipe,HANDLE_FLAG_INHERIT,0);
    HANDLE input=CreateFileW(L"NUL",GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,OPEN_EXISTING,0,NULL);
    STARTUPINFOW start={0};start.cb=sizeof start;start.dwFlags=STARTF_USESTDHANDLES;start.hStdInput=input;start.hStdOutput=write_pipe;start.hStdError=write_pipe;
    PROCESS_INFORMATION process={0};BOOL opened=CreateProcessW(python,command,NULL,NULL,TRUE,CREATE_NO_WINDOW,NULL,root,&start,&process);
    CloseHandle(write_pipe);if(input!=INVALID_HANDLE_VALUE)CloseHandle(input);
    if(!opened){CloseHandle(read_pipe);read_pipe=NULL;set_status(L"Could not load settings. Keep all launcher files together.",1);return;}
    child=process.hProcess;CloseHandle(process.hThread);child_mode=save?2:1;settings_output_length=0;settings_output[0]=0;
    set_status(save?L"Saving your settings...":L"Loading your saved settings...",0);layout();
}
static void settings_finish(DWORD code){
    int operation=child_mode;child_mode=0;int parsed[LOA_SETTINGS_COUNT],end=0;char token[65]={0};
    int count=sscanf(settings_output,"LOA_SETTINGS 1 %64s %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d%n",token,
        &parsed[0],&parsed[1],&parsed[2],&parsed[3],&parsed[4],&parsed[5],&parsed[6],&parsed[7],&parsed[8],&parsed[9],&parsed[10],&parsed[11],&parsed[12],&parsed[13],&parsed[14],&end);
    int valid=!code&&count==16&&(!strcmp(token,"missing")||(strlen(token)==64&&strspn(token,"0123456789abcdef")==64));
    for(int i=0;valid&&i<LOA_SETTINGS_COUNT;i++)if(parsed[i]<0||parsed[i]>=loa_setting_lengths[i])valid=0;
    if(!valid){
        settings_loaded=0;wchar_t error[2048];settings_text(settings_output,error,2048);set_status(error[0]?error:L"Settings could not be read. No changes were saved.",1);
    }else{
        memcpy(settings_codes,parsed,sizeof parsed);memcpy(settings_saved,parsed,sizeof parsed);strcpy(settings_token,token);settings_loaded=1;
        const char *controls=strchr(settings_output+end,'\n');settings_text(controls?controls+1:"",settings_controls,4096);
        set_status(operation==2?L"Settings saved. They will be used the next time you launch.":L"Change options with Left / Right or select a row to cycle.",0);
    }
    layout();RedrawWindow(main_window,NULL,NULL,RDW_INVALIDATE|RDW_ALLCHILDREN|RDW_UPDATENOW);
}
static int settings_command(int id){
    if(id==ID_SETTINGS){
        if(!child){settings_page=1;settings_tab=0;settings_loaded=0;expanded=0;layout();settings_request(0);}return 1;
    }
    if(!settings_page)return 0;
    if(id==ID_SETTINGS_BACK){
        if(!child){memcpy(settings_codes,settings_saved,sizeof settings_codes);settings_page=0;set_status(L"Game files will be checked before launch.",0);layout();RedrawWindow(main_window,NULL,NULL,RDW_INVALIDATE|RDW_ALLCHILDREN|RDW_UPDATENOW);SetFocus(play_button);}return 1;
    }
    if(id==ID_SETTINGS_SAVE){if(!child&&settings_dirty())settings_request(1);return 1;}
    if(id>=ID_SETTINGS_TAB&&id<ID_SETTINGS_TAB+5){if(!child&&settings_loaded){settings_tab=id-ID_SETTINGS_TAB;layout();RedrawWindow(main_window,NULL,NULL,RDW_INVALIDATE|RDW_ALLCHILDREN|RDW_UPDATENOW);}return 1;}
    if(id>=ID_SETTING_ROW&&id<ID_SETTING_ROW+LOA_SETTINGS_COUNT){if(IsWindowVisible(settings_rows[id-ID_SETTING_ROW]))settings_change(id-ID_SETTING_ROW,0);return 1;}
    if(id>=ID_PRESET&&id<ID_PRESET+3){if(!child&&settings_loaded&&settings_tab==3){loa_settings_preset(settings_codes,id-ID_PRESET);settings_changed();}return 1;}
    return 0;
}
