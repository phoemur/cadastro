#!/usr/bin/env python3

import os
import datetime
import tkinter
import sqlite3
import xml.etree.ElementTree
import xml.parsers.expat
import xml.sax.saxutils

from tkinter import ttk, messagebox
from tkinter.filedialog import asksaveasfilename, askopenfilename

class AbrirWindow(tkinter.Toplevel):
    
    def __init__(self, parent, name=None):
        super().__init__(parent)
        self.title("Localizar Paciente")
        self.parent = parent
        self.accepted = False
        self.nameVar = tkinter.StringVar()
        if name is not None:
            self.nameVar.set(name)
        
        frame = tkinter.Frame(self)
        nameLabel = tkinter.Label(frame, text="Nome:", underline=0)
        nameEntry = tkinter.Entry(frame, textvariable=self.nameVar)
        nameEntry.focus_set()
        okButton = tkinter.Button(frame, text="Localizar", command=self.ok)
        cancelButton = tkinter.Button(frame, text="Cancelar", command=self.close)
        nameLabel.grid(row=0, column=0, sticky=tkinter.W, pady=3,padx=3)
        nameEntry.grid(row=0, column=1, columnspan=3, sticky=tkinter.EW, pady=3, padx=3)
        okButton.grid(row=2, column=2, sticky=tkinter.EW, pady=3, padx=3)
        cancelButton.grid(row=2, column=3, sticky=tkinter.EW, pady=3, padx=3)
        frame.grid(row=0, column=0, sticky=tkinter.NSEW)
        frame.columnconfigure(1, weight=1)
        window = self.winfo_toplevel()
        window.columnconfigure(0, weight=1)
        
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.close)

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.grab_set()
        self.wait_window(self)

    def ok(self, event=None):
        self.name = self.nameVar.get()
        self.accepted = True
        self.close()

    def close(self, event=None):
        self.parent.focus_set()
        self.destroy()       

class MainWindow(tkinter.Tk):
    
    def __init__(self):
        self.filename = os.path.join(os.path.dirname(__file__), "patients.sdb")
        self.db = self.connect(self.filename)
        
        tkinter.Tk.__init__(self)
        self.wm_title("Cadastro de pacientes")
        self.protocol("WM_DELETE_WINDOW", self.sair)
        self.resizable(tkinter.FALSE, tkinter.FALSE)
        
        self.images_keepmem = []
        self.icon = tkinter.PhotoImage(file=os.path.join(os.path.dirname(__file__), "images", "bookmark.gif"))
        self.images_keepmem.append(self.icon)
        self.tk.call('wm', 'iconphoto', self._w, self.icon)
        
        #Menus
        menubar = tkinter.Menu(self)
        self["menu"] = menubar
        self.option_add('*tearOff', tkinter.FALSE)
        
        #Menu Arquivo
        menuArquivo = tkinter.Menu(menubar)
        for label, command, shortcut_text, shortcut in (
                ("Novo", self.novo, "Ctrl+N", "<Control-n>"),
                ("Abrir", self.abrir, "Ctrl+A", "<Control-a>"),
                ("Salvar", self.salvar, "Ctrl+S", "<Control-s>"),
                ("Excluir", self.remover, "Ctrl+E", "<Control-e>"),
                (None, None, None, None),
                ("Fechar", self.sair, "Ctrl+Q", "<Control-q>")):
            if label is None:
                menuArquivo.add_separator()
            else:
                menuArquivo.add_command(label=label, underline=0,
                        command=command, accelerator=shortcut_text)
                self.bind(shortcut, command)        
        menubar.add_cascade(label="Arquivo", menu=menuArquivo, underline=0)
        
        # Menu Editar
        menuEditar = tkinter.Menu(menubar)
        for label, command, shortcut_text, shortcut in (
                ("Copiar", self.copiar, "Ctrl+C", "<Control-c>"),
                ("Colar", self.colar, "Ctrl+V", "<Control-v>"),
                ("Recortar", self.recortar, "Ctrl+X", "<Control-x>")):
            menuEditar.add_command(label=label, underline=0 if label != "Colar" else 1,
                        command=command, accelerator=shortcut_text)
            #self.bind(shortcut, command)
        menuEditar.add_separator()
        menuEditar.add_command(label="Importar XML", underline=0, command=self.importar_db)
        menuEditar.add_command(label="Exportar XML", underline=0, command=self.exportar_db)
        
        menubar.add_cascade(label="Editar", menu=menuEditar, underline=0)
        
        #Menu Ajuda
        menuAjuda = tkinter.Menu(menubar)
        menuAjuda.add_command(label="Sobre", underline=0,
                              command=self.sobre, accelerator="Ctrl+H")
        self.bind("<Control-h>", self.sobre)
        menubar.add_cascade(label="Ajuda", menu=menuAjuda, underline=2)
        
        #Menu Mouse
        self.MENUmouse = tkinter.Menu(self, tearoff=0)
        self.MENUmouse.add_command(label="Copiar")
        self.MENUmouse.add_command(label="Colar")
        self.MENUmouse.add_command(label="Recortar")
        self.bind("<Button-3><ButtonRelease-3>", self.show_mouse_menu)
        
        # Toolbar
        self.mainframe = tkinter.Frame(self)
        self.toolbar = tkinter.Frame(self.mainframe)
        for image, command in (
                ("images/filenew.gif", self.novo),
                ("images/fileopen.gif", self.abrir),
                ("images/trash.gif", self.remover),
                ("images/filesave.gif", self.salvar),
                ("images/exit.gif", self.sair)):
            image = os.path.join(os.path.dirname(__file__), image)
            try:
                image = tkinter.PhotoImage(file=image)
                self.images_keepmem.append(image)
                button = tkinter.Button(self.toolbar, image=image,
                                        command=command)
                button.grid(row=0, column=len(self.images_keepmem) -2)
            except tkinter.TclError as err:
                print(err)
        
        self.toolbar.grid(row=0, column=0, columnspan=5, sticky=tkinter.NW)
        self.mainframe.grid(row=0,column=0, sticky=tkinter.EW)
        
        #Nome
        ttk.Label(self.mainframe, text="Nome: ").grid(row=1, column=1, sticky=tkinter.E) 
        self.nome = tkinter.StringVar()
        self.name_entry = ttk.Combobox(self.mainframe, width=50, textvariable=self.nome)
        self.name_entry.grid(row=1, column=2, columnspan=9, sticky=tkinter.W)
        self.name_entry['values'] = self.list_pac(self.db)
        self.name_entry.bind('<<ComboboxSelected>>', self.abrir_nome)
        
        #Sexo
        ttk.Label(self.mainframe, text='Sexo: ').grid(row=2, column=1, sticky=tkinter.E)
        self.sexo = tkinter.StringVar()
        self.masculino = ttk.Radiobutton(self.mainframe, text='Masculino', variable=self.sexo, value='Masculino')
        self.feminino = ttk.Radiobutton(self.mainframe, text='Feminino', variable=self.sexo, value='Feminino')
        self.masculino.grid(row=2, column=2, sticky=tkinter.W)
        self.feminino.grid(row=2, column=3, sticky=tkinter.W)
        
        #Plano de Saúde
        ttk.Label(self.mainframe, text='Plano: ').grid(row=3, column=1, sticky=tkinter.E)
        self.plano = tkinter.StringVar()
        self.plano_entry = ttk.Combobox(self.mainframe, textvariable=self.plano)
        self.plano_entry.grid(row=3, column=2, columnspan=3, sticky=tkinter.W)
        self.plano_entry['values'] = self.list_planos(self.db)
        
        # Número do Cartão
        ttk.Label(self.mainframe, text='Cartão: ').grid(row=4, column=1, sticky=tkinter.E)
        self.cartao = tkinter.StringVar()
        ttk.Entry(self.mainframe, width=20, textvariable=self.cartao).grid(row=4,column=2, columnspan=3, sticky=tkinter.W)
        
        #Data de nascimento
        self.ageframe = tkinter.Frame(self.mainframe)
        self.ageframe.grid(row=5, column=1, columnspan=10, sticky=tkinter.EW)
        ttk.Label(self.ageframe, text='Data de Nascimento: ').grid(row=1, column=1, sticky=tkinter.E)
        self.dia_nasc = tkinter.StringVar()
        self.dia_nasc.set('01')
        self.mes_nasc = tkinter.StringVar()
        self.mes_nasc.set('Janeiro')
        self.ano_nasc = tkinter.StringVar()
        self.ano_nasc.set('1950')
        self.idade = tkinter.StringVar()
        ttk.Entry(self.ageframe, width=4, textvariable=self.dia_nasc).grid(row=1,column=2, sticky=tkinter.E)
        ttk.Label(self.ageframe, text='/').grid(row=1, column=3, sticky=tkinter.EW)
        self.mes = ttk.Combobox(self.ageframe, textvariable=self.mes_nasc)
        self.mes.grid(row=1, column=4, sticky=tkinter.EW)
        ttk.Label(self.ageframe, text='/').grid(row=1, column=5, sticky=tkinter.EW)
        ttk.Entry(self.ageframe, width=6, textvariable=self.ano_nasc).grid(row=1,column=6, sticky=tkinter.W)
        self.mes['values'] = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                              'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')
        
        ttk.Label(self.ageframe, text='Idade: ').grid(row=1, column=7, sticky=tkinter.E)
        ttk.Label(self.ageframe, textvariable=self.idade).grid(row=1, column=8, sticky=tkinter.W)
        ttk.Label(self.ageframe, text='anos').grid(row=1, column=9, sticky=tkinter.E)
        self.mes.bind('<<ComboboxSelected>>', self.callback)
        self.dia_nasc.trace("w", self.callback)
        self.ano_nasc.trace("w", self.callback)
        self.callback()
        
        #Endereço
        ttk.Label(self.mainframe, text='Endereço: ').grid(row=6, column=1, sticky=tkinter.E)
        self.endereco = tkinter.StringVar()
        ttk.Entry(self.mainframe, width=50, textvariable=self.endereco).grid(row=6, column=2, columnspan=9, sticky=tkinter.W)
        
        #Cidade
        ttk.Label(self.mainframe, text='Cidade: ').grid(row=7, column=1, sticky=tkinter.E)
        self.cidade = tkinter.StringVar()
        ttk.Entry(self.mainframe, width=30, textvariable=self.cidade).grid(row=7, column=2, sticky=tkinter.W)
        
        # Estado
        ttk.Label(self.mainframe, text='Estado: ').grid(row=7, column=3, sticky=tkinter.E)
        self.estado = tkinter.StringVar()
        self.estado_entry = ttk.Combobox(self.mainframe, width=4, textvariable=self.estado)
        self.estado_entry.grid(row=7, column=4, sticky=tkinter.W)
        self.estado_entry['values'] = ('AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
                                       'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO')
        
        # CEP
        ttk.Label(self.mainframe, text='CEP: ').grid(row=8, column=1, sticky=tkinter.E)
        self.cep = tkinter.StringVar()
        ttk.Entry(self.mainframe, width=30, textvariable=self.cep).grid(row=8, column=2, sticky=tkinter.W)
        
        # Telefone
        ttk.Label(self.mainframe, text='Telefone: ').grid(row=9, column=1, sticky=tkinter.E)
        self.telefone = tkinter.StringVar()
        ttk.Entry(self.mainframe, width=20, textvariable=self.telefone).grid(row=9, column=2, columnspan=3, sticky=tkinter.W)
        
        # Celular
        ttk.Label(self.mainframe, text='Celular: ').grid(row=10, column=1, sticky=tkinter.E)
        self.celular = tkinter.StringVar()
        ttk.Entry(self.mainframe, width=20, textvariable=self.celular).grid(row=10, column=2, columnspan=3, sticky=tkinter.W)
        
        # Registro
        ttk.Label(self.mainframe, text='Registro: ').grid(row=10, column=5, sticky=tkinter.E)
        self.registro = tkinter.StringVar()
        self.reg_entry = ttk.Combobox(self.mainframe, width=5, textvariable=self.registro)
        self.reg_entry.grid(row=10, column=6, sticky=tkinter.W)
        self.reg_entry['values'] = self.list_id(self.db)
        self.reg_entry.bind('<<ComboboxSelected>>', self.abrir_id)
        
        for child in self.mainframe.winfo_children():
            child.grid_configure(padx=3, pady=3)
            
        for child in self.toolbar.winfo_children():
            child.grid_configure(padx=2, pady=3)
    
    def __del__(self):
        if self.db is not None:
            self.db.close()
    
    def connect(self, filename):
        create = not os.path.exists(filename)
        db = sqlite3.connect(filename)
        if create:
            cursor = db.cursor()
            cursor.execute("CREATE TABLE planos ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL, "
                "nome TEXT UNIQUE NOT NULL)")
            cursor.execute("CREATE TABLE pacientes ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL, "
                "nome TEXT NOT NULL, "
                "sexo TEXT, "
                "cartao TEXT, "
                "dia_nasc TEXT, "
                "mes_nasc TEXT, "
                "ano_nasc TEXT, "
                "endereco TEXT, "
                "cidade TEXT, "
                "estado TEXT, "
                "cep TEXT, "
                "telefone TEXT NOT NULL, "
                "celular TEXT, "
                "plano_id INTEGER NOT NULL, "
                "FOREIGN KEY (plano_id) REFERENCES planos)")
            db.commit()
        return db
    
    def get_and_set_plano(self, db, plano):
        plano_id = self.get_plano_id(db, plano.upper())
        if plano_id is not None:
            return plano_id
        cursor = db.cursor()
        cursor.execute("INSERT INTO planos (nome) VALUES (?)",
                    (plano.upper(),))
        db.commit()
        return self.get_plano_id(db, plano)

    def get_plano_id(self, db, plano):
        cursor = db.cursor()
        cursor.execute("SELECT id FROM planos WHERE nome=?", (plano.upper(),))
        fields = cursor.fetchone()
        return fields[0] if fields is not None else None
    
    def list_id(self, db):
        lista = []
        cursor = db.cursor()
        cursor.execute("SELECT id FROM pacientes ORDER BY id")
        for fields in cursor:
            lista.append(fields[0])
        return tuple(lista)
    
    def list_planos(self, db):
        lista = []
        cursor = db.cursor()
        cursor.execute("SELECT nome FROM planos ORDER BY nome")
        for fields in cursor:
            lista.append(fields[0])
        return tuple(lista)
    
    def list_pac(self, db):
        lista = []
        cursor = db.cursor()
        cursor.execute("SELECT nome FROM pacientes ORDER BY nome")
        for record in cursor:
            lista.append(record[0])
        return tuple(lista)
    
    def pac_count(self, db):
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM pacientes")
        return cursor.fetchone()[0]
    
    def find_pac_id(self, nome, telefone):
        cursor = self.db.cursor()
        cursor.execute('SELECT nome, telefone, id FROM pacientes '
                       'WHERE nome=? AND telefone=?',
                       (nome, telefone))
        records = cursor.fetchall()
        if len(records) == 0:
            return None
        elif len(records) > 1:
            raise ValueError('Nome duplicado no banco de dados')
        else:
            return records[0][2]
    
    def copiar(self, *ignore):
        w = self.focus_get()
        w.event_generate("<<Copy>>")
    
    def colar(self, *ignore):
        w = self.focus_get()
        w.event_generate("<<Paste>>")
    
    def recortar(self, *ignore):
        w = self.focus_get()
        w.event_generate("<<Cut>>")
    
    def sobre(self, *ignore):
        messagebox.showinfo(message='Cadastro de Pacientes versão 0.10', title='Sobre')
    
    def blank(self, *ignore):
        self.nome.set('')
        self.sexo.set(None)
        self.cartao.set('')
        self.dia_nasc.set('01')
        self.mes_nasc.set('Janeiro')
        self.ano_nasc.set('1950')
        self.endereco.set('')
        self.cidade.set('')
        self.plano.set('')
        self.estado.set('')
        self.cep.set('')
        self.telefone.set('')
        self.celular.set('')
        self.registro.set('')
        
        self.name_entry['values'] = self.list_pac(self.db)
        self.reg_entry['values'] = self.list_id(self.db)
        self.plano_entry['values'] = self.list_planos(self.db)
        
    def novo(self, *ignore):
        reply = messagebox.askyesno('Novo', 
                     'Deseja salvar alterações para o paciente {0}?'.format(self.nome.get()), parent=self)
        if reply and len(self.nome.get()) > 0:
            self.salvar(self) 
        self.blank()
    
    def abrir(self, *ignore):
        form = AbrirWindow(self)
        if form.accepted and form.name:
            nome = form.name
        else:
            return
        
        cursor = self.db.cursor()
        cursor.execute('SELECT nome, id FROM pacientes '
                       'WHERE nome LIKE ? ORDER BY nome',
                       (nome + "%", ))
        records = cursor.fetchall()
        if len(records) > 1:
            ids = []
            for i in range(len(records)):
                ids.append(str(records[i][1]))
            messagebox.showinfo(message='Há mais de um paciente com o nome {0} Registros: ({1}) Tente abrir pelo número do registro'\
                                                                                        .format(nome, ', '.join(ids)), title='Atenção')
        else:
            self.registro.set(records[0][1])
            self.abrir_id()       
    
    def abrir_nome(self, *ignore):
        nome = self.nome.get()  
        cursor = self.db.cursor()
        cursor.execute('SELECT nome, id FROM pacientes '
                       'WHERE nome=? ORDER BY nome',
                       (nome, ))
        records = cursor.fetchall()
        if len(records) > 1:
            ids = []
            for i in range(len(records)):
                ids.append(str(records[i][1]))
            messagebox.showinfo(message='Há mais de um paciente com o nome {0} Registros: ({1}) Tente abrir pelo número do registro'\
                                                                                        .format(nome, ', '.join(ids)), title='Atenção')
        else:
            self.registro.set(records[0][1])
            self.abrir_id()
    
    def abrir_id(self, *ignore):            
        cursor = self.db.cursor()
        cursor.execute("SELECT pacientes.nome, pacientes.sexo, pacientes.cartao, pacientes.dia_nasc, pacientes.mes_nasc, "
                       "pacientes.ano_nasc, pacientes.endereco, pacientes.cidade, planos.nome, pacientes.estado, "
                       "pacientes.cep, pacientes.telefone, pacientes.celular "
                       "FROM pacientes, planos "
                       "WHERE pacientes.plano_id = planos.id AND "
                       "pacientes.id=?", (self.registro.get(),))
        nome, sexo, cartao, dia_nasc, mes_nasc, ano_nasc, endereco, cidade, plano, estado, cep, telefone, celular = cursor.fetchone()
        self.nome.set(nome)
        self.sexo.set(sexo)
        self.cartao.set(cartao)
        self.dia_nasc.set(dia_nasc)
        self.mes_nasc.set(mes_nasc)
        self.ano_nasc.set(ano_nasc)
        self.endereco.set(endereco)
        self.cidade.set(cidade)
        self.plano.set(plano)
        self.estado.set(estado)
        self.cep.set(cep)
        self.telefone.set(telefone)
        self.celular.set(celular)
        
        self.name_entry['values'] = self.list_pac(self.db)
        self.reg_entry['values'] = self.list_id(self.db)
        self.plano_entry['values'] = self.list_planos(self.db)
    
    def remover(self, *ignore):
        reply = messagebox.askyesno('Remover', 
                     'Deseja remover o paciente atual do Banco de Dados?', parent=self)
        
        if not reply:
            return
        nome = self.nome.get()
        telefone = self.telefone.get()
        reg = self.registro.get()
        identity = reg if len(reg) != 0 else self.find_pac_id(nome, telefone)
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM pacientes WHERE id=?", (identity,))
        self.db.commit()
        self.blank()
        
    def salvar(self, *ignore):
        nome = self.nome.get()
        if not nome:
            messagebox.showwarning(title='Atenção', message='É obrigatório preencher o nome')
            return
        sexo = self.sexo.get()
        cartao = self.cartao.get()
        dia_nasc = self.dia_nasc.get()
        mes_nasc = self.mes_nasc.get()
        ano_nasc = self.ano_nasc.get()
        endereco = self.endereco.get()
        cidade = self.cidade.get()
        estado = self.estado.get()
        cep = self.cep.get()
        telefone = self.telefone.get()
        if not telefone:
            messagebox.showwarning(title='Atenção', message='É obrigatório preencher o telefone')
            return
        celular = self.celular.get()
        plano_id = self.get_and_set_plano(self.db, self.plano.get())
        
        identity = self.registro.get() if len(self.registro.get()) != 0 else self.find_pac_id(nome, telefone)
        
        if identity is None:
            cursor = self.db.cursor()
            cursor.execute("INSERT INTO pacientes "
                    "(nome, sexo, cartao, dia_nasc, mes_nasc, ano_nasc, endereco, cidade, estado, cep, telefone, celular, plano_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (nome, sexo, cartao, dia_nasc, mes_nasc, ano_nasc, endereco, cidade,
                        estado, cep, telefone, celular, plano_id))
            self.db.commit()
        else:
            cursor = self.db.cursor()
            cursor.execute("UPDATE pacientes SET nome=:nome, sexo=:sexo, cartao=:cartao, dia_nasc=:dia_nasc, mes_nasc=:mes_nasc, "
                   "ano_nasc=:ano_nasc, endereco=:endereco, cidade=:cidade, estado=:estado, cep=:cep, telefone=:telefone, " 
                   "celular=:celular, plano_id=:plano_id "
                   "WHERE id=:identity", locals())
            self.db.commit()
            
        self.name_entry['values'] = self.list_pac(self.db)
        self.reg_entry['values'] = self.list_id(self.db)
        self.plano_entry['values'] = self.list_planos(self.db)
            
    def sair(self, event=None):
        if self.okayToContinue():
            self.destroy()
            
    def okayToContinue(self):
        reply = messagebox.askyesnocancel(
                   "Saída",
                   "Deseja salvar as alterações antes de sair?", parent=self)
        if reply is None:
            return False
        elif reply and len(self.nome.get()) > 0:
            self.salvar(self)
            return True
        else:
            return True
    
    def show_mouse_menu(self, e):
        w = e.widget
        self.MENUmouse.entryconfigure("Copiar", command=lambda: w.event_generate("<<Copy>>"))
        self.MENUmouse.entryconfigure("Colar", command=lambda: w.event_generate("<<Paste>>"))
        self.MENUmouse.entryconfigure("Recortar", command=lambda: w.event_generate("<<Cut>>"))
        self.MENUmouse.tk.call("tk_popup", self.MENUmouse, e.x_root, e.y_root)
        
    def callback(self, *ignore):
        try:
            self.mes_idade = int(self.mes['values'].index(self.mes_nasc.get())) + 1
            self.n = datetime.date.today() - datetime.date(int(self.ano_nasc.get()), self.mes_idade, int(self.dia_nasc.get()))
            self.idade.set(str(self.n.days / 365.25)[:5])
        except:
            self.idade.set('Invalid')
            
    def importar_db(self, *ignore):
        reply = messagebox.askyesno(title='Info', message='Esta ação irá apagar o banco de dados atual e importar um novo XML. Deseja continuar?')
        if not reply:
            return
        
        options = {}
        options['filetypes'] = [('Arquivos XML', '.xml'), ('Todos Arquivos', '.*')]
        options['initialfile'] = 'patients.xml'
        fileName = askopenfilename(**options)
        if not fileName:
            return
        
        try:
            tree = xml.etree.ElementTree.parse(fileName)
        except (EnvironmentError, xml.parsers.expat.ExpatError, xml.etree.ElementTree.ParseError) as err:
            messagebox.showwarning(title='Erro', message='ERRO: {0}. Não foi possível importar o banco de dados'.format(err))
            return
        
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM planos")
        cursor.execute("DELETE FROM pacientes")
    
        for element in tree.findall("pac"):
            self.get_and_set_plano(self.db, element.get("plano"))
            
        for element in tree.findall("pac"):
            try:           
                nome = element.text.strip()
                sexo = element.get("sexo")
                cartao = element.get("cartao")
                dia_nasc = element.get("dia_nasc")
                mes_nasc = element.get("mes_nasc")
                ano_nasc = element.get("ano_nasc")
                endereco = element.get("endereco")
                cidade = element.get("cidade")
                estado = element.get("estado")
                cep = element.get("cep")
                telefone = element.get("telefone")
                celular = element.get("celular")
                plano_id = self.get_plano_id(self.db, element.get("plano"))
                cursor.execute("INSERT INTO pacientes "
                    "(nome, sexo, cartao, dia_nasc, mes_nasc, ano_nasc, endereco, cidade, estado, cep, telefone, celular, plano_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (nome, sexo, cartao, dia_nasc, mes_nasc, ano_nasc, endereco, cidade,
                        estado, cep, telefone, celular, plano_id))
            except ValueError as err:
                self.db.rollback()
                messagebox.showwarning(title='Erro', message='ERRO: {0}. Não foi possível importar o banco de dados'.format(err))
                break
        else:
            self.db.commit()
            self.name_entry['values'] = self.list_pac(self.db)
            self.reg_entry['values'] = self.list_id(self.db)
            self.plano_entry['values'] = self.list_planos(self.db)
            messagebox.showinfo(title='Info', message='Arquivo XML importado com sucesso. Foram importados {0} pacientes'.format(self.pac_count(self.db)))
            
    def exportar_db(self, *ignore):
        options = {}
        options['filetypes'] = [('Arquivos XML', '.xml'), ('Todos Arquivos', '.*')]
        options['initialfile'] = 'patients.xml'
        fileName = asksaveasfilename(**options)
        if not fileName:
            return
        
        cursor = self.db.cursor()
        cursor.execute("SELECT pacientes.nome, pacientes.sexo, pacientes.cartao, pacientes.dia_nasc, pacientes.mes_nasc, "
                       "pacientes.ano_nasc, pacientes.endereco, pacientes.cidade, planos.nome, pacientes.estado, "
                       "pacientes.cep, pacientes.telefone, pacientes.celular "
                       "FROM pacientes, planos "
                       "WHERE pacientes.plano_id = planos.id "
                       "ORDER BY pacientes.nome ")
        
        try:
            with open(fileName, mode="w", encoding="UTF-8") as fh:
                fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                fh.write("<pacientes>\n")
                for record in cursor:
                    fh.write('<pac sexo={0} cartao={1} '
                            'dia_nasc={2} mes_nasc={3} ano_nasc={4} '
                            'endereco={5} cidade={6} plano={7} estado={8} '
                            'cep={9} telefone={10} celular={11}>'.format(
                            xml.sax.saxutils.quoteattr(record[1]),
                            xml.sax.saxutils.quoteattr(record[2]),
                            xml.sax.saxutils.quoteattr(record[3]),
                            xml.sax.saxutils.quoteattr(record[4]),
                            xml.sax.saxutils.quoteattr(record[5]),
                            xml.sax.saxutils.quoteattr(record[6]),
                            xml.sax.saxutils.quoteattr(record[7]),
                            xml.sax.saxutils.quoteattr(record[8]),
                            xml.sax.saxutils.quoteattr(record[9]),
                            xml.sax.saxutils.quoteattr(record[10]),
                            xml.sax.saxutils.quoteattr(record[11]),
                            xml.sax.saxutils.quoteattr(record[12])))
                    fh.write(xml.sax.saxutils.escape(record[0]))
                    fh.write("</pac>\n")
                fh.write("</pacientes>\n")
            messagebox.showinfo(title='Info', message='Arquivo XML exportado com sucesso')
        except EnvironmentError as err:
            messagebox.showwarning(title='Erro', message='ERRO: {0}. Não foi possível exportar o banco de dados'.format(err))
                    
if __name__ == '__main__':
    app = MainWindow()
    app.mainloop()
